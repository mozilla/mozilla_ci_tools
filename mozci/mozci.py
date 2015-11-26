"""
This module is generally your starting point.

In here, you will also find high level functions that will do various low level
interactions with distinct modules to meet your needs.
"""
from __future__ import absolute_import

import logging

from buildapi_client import make_retrigger_request, trigger_arbitrary_job

from mozci import repositories
from mozci.errors import MozciError
from mozci.platforms import (
    build_talos_buildernames_for_repo,
    determine_upstream_builder,
    is_downstream,
    list_builders,
)
from mozci.sources import buildjson, pushlog
from mozci.query_jobs import (
    PENDING,
    RUNNING,
    SUCCESS,
    WARNING,
    UNKNOWN,
    COALESCED,
    FAILURE,
    EXCEPTION,
    RETRY,
    BuildApi,
    TreeherderApi
)
from mozci.utils.misc import _all_urls_reachable
from mozci.utils.transfer import path_to_file, clean_directory

LOG = logging.getLogger('mozci')
SCHEDULING_MANAGER = {}

# Default value of QUERY_SOURCE
QUERY_SOURCE = BuildApi()

# Set this value to False in your tool to prevent any sort of validation
VALIDATE = True


def disable_validations():
    global VALIDATE
    if VALIDATE:
        LOG.debug("Disable validations.")
        VALIDATE = False


def set_query_source(query_source="buildapi"):
    """ Function to set the global QUERY_SOURCE """
    global QUERY_SOURCE
    if query_source == "treeherder":
        source_class = TreeherderApi
    else:
        source_class = BuildApi
    QUERY_SOURCE = source_class()


def _unique_build_request(buildername, revision):
    """
    We want to prevent requesting a build job too many times
    in the same session.
    """
    global SCHEDULING_MANAGER
    sch_mgr = SCHEDULING_MANAGER

    if is_downstream(buildername):
        return True
    else:
        if revision in sch_mgr and buildername in sch_mgr[revision]:
            LOG.debug("We have already scheduled the build '%s' for "
                      "revision %s during this session. We don't allow "
                      "multiple requests." % (buildername, revision))
            return False
        return True


def _status_summary(jobs):
    """Return the number of successful, pending and running jobs."""
    assert type(jobs) == list
    successful = 0
    pending = 0
    running = 0
    coalesced = 0
    failed = 0

    for job in jobs:
        status = QUERY_SOURCE.get_job_status(job)
        if status == PENDING:
            pending += 1
        if status in (RUNNING, UNKNOWN):
            running += 1
        if status == SUCCESS:
            successful += 1
        if status == COALESCED:
            coalesced += 1
        if status in (FAILURE, WARNING, EXCEPTION, RETRY):
            failed += 1

    return (successful, pending, running, coalesced, failed)


def determine_trigger_objective(revision, buildername, trigger_build_if_missing=True):
    """
    Determine if we need to trigger any jobs and which job.

    Returns:

    * The name of the builder we need to trigger
    * Files, if needed, to trigger such builder
    """
    builder_to_trigger = None
    files = None
    repo_name = query_repo_name_from_buildername(buildername)

    build_buildername = determine_upstream_builder(buildername)

    if VALIDATE and not valid_builder(build_buildername):
        raise MozciError("Our platforms mapping system has failed.")

    if build_buildername == buildername:
        # For a build job we know that we don't need files to
        # trigger it and it's the build job we want to trigger
        return build_buildername, None

    # Let's figure out which jobs are associated to such revision
    query_api = BuildApi()
    # Let's only look at jobs that match such build_buildername
    build_jobs = query_api.get_matching_jobs(repo_name, revision, build_buildername)

    # We need to determine if we need to trigger a build job
    # or the test job
    working_job = None
    running_job = None
    failed_job = None

    LOG.debug("List of matching jobs:")
    for job in build_jobs:
        try:
            status = query_api.get_job_status(job)
        except buildjson.BuildjsonException:
            LOG.debug("We have hit bug 1159279 and have to work around it. We will "
                      "pretend that we could not reach the files for it.")
            continue

        # Sometimes running jobs have status unknown in buildapi
        if status in (RUNNING, PENDING, UNKNOWN):
            LOG.debug("We found a running/pending build job. We don't search anymore.")
            running_job = job
            # We cannot call _find_files for a running job
            continue

        # Having a coalesced build is the same as not having a build available
        if status == COALESCED:
            LOG.debug("The build we found was a coalesced one; this is the same as "
                      "non-existant.")
            continue

        # Successful or failed jobs may have the files we need
        files = _find_files(job)
        if files != [] and _all_urls_reachable(files):
            working_job = job
            break
        else:
            LOG.debug("We can't determine the files for this build or "
                      "can't reach them.")
            files = None

        LOG.info("We found a job that finished but it did not "
                 "produced files. status: %d" % status)
        failed_job = job
    # End of for loop

    if working_job:
        # We found a build job with the necessary files. It could be a
        # successful job, a running job that already emitted files or a
        # testfailed job
        LOG.debug(str(working_job))
        LOG.info("We have the necessary files to trigger the downstream job.")
        # We have the files needed to trigger the test job
        builder_to_trigger = buildername

    elif running_job:
        LOG.info("We found a running/pending build job. We will not trigger another one.")
        LOG.info("You have to run the script again after the build job is finished to "
                 "trigger %s." % buildername)
        builder_to_trigger = None

    elif failed_job:
        LOG.info("The build job %s failed on revision %s without generating the "
                 "necessary files. We will not trigger anything." %
                 (build_buildername, revision))
        builder_to_trigger = None

    else:
        # We were trying to build a test job, however, we determined
        # that we need an upstream builder instead
        if not trigger_build_if_missing or not _unique_build_request(build_buildername, revision):
            # This is a safeguard to prevent triggering a build
            # job multiple times if it is not intentional
            builder_to_trigger = None
            if not trigger_build_if_missing:
                LOG.info("We would have to triggered build '%s' in order to trigger "
                         "job '%s'. On this mode we will not trigger either." %
                         (build_buildername, buildername))
        else:
            LOG.info("We will trigger 1) "
                     "'%s' instead of 2) '%s'" % (build_buildername, buildername))
            LOG.info("We need to trigger the build job once (1) "
                     "in order to be able to run the test job (2).")
            if repo_name == 'try':
                LOG.info("You'll need to run the script again after (1) is done to "
                         "trigger (2).")
            else:
                LOG.info("After (1) is done and if no coalesccing happens the test "
                         "jobs associated with it will be triggered.")
            builder_to_trigger = build_buildername

    return builder_to_trigger, files


def _status_info(job_schedule_info):
    # Let's grab the last job
    complete_at = job_schedule_info["requests"][0]["complete_at"]
    request_id = job_schedule_info["requests"][0]["request_id"]

    # NOTE: This call can take a bit of time
    return buildjson.query_job_data(complete_at, request_id)


def _find_files(job_schedule_info):
    """
    Find the files needed to trigger a job.

    Raises MozciError if the job status doesn't have a properties key.
    """
    files = []

    job_status = _status_info(job_schedule_info)
    assert job_status is not None, \
        "We should not have received an empty status"

    properties = job_status.get("properties")

    if not properties:
        LOG.error(str(job_status))
        raise MozciError("The status of the job is expected to have a "
                         "properties key, however, it is missing.")

    LOG.debug("We want to find the files needed to trigger %s" %
              properties["buildername"])

    # We need the packageUrl, and one of testsUrl and testPackagesUrl,
    # preferring testPackagesUrl.
    if "packageUrl" in properties:
        files.append(properties["packageUrl"])

    if "testPackagesUrl" in properties:
        files.append(properties["testPackagesUrl"])
    elif "testsUrl" in properties:
        files.append(properties["testsUrl"])

    return files


#
# Query functionality
#
def query_builders(repo_name=None):
    """Return list of all builders or the builders associated to a repo."""
    return list_builders(repo_name)


def query_repo_name_from_buildername(buildername, clobber=False):
    """
    Return the repository name from a given buildername.

    Raises MozciError if there is no repository name in buildername.
    """
    repositories_list = repositories.query_repositories(clobber)
    ret_val = None
    for repo_name in repositories_list:
        if any(True for iterable in [' %s ', '_%s_', '-%s-']
               if iterable % repo_name in buildername):
            ret_val = repo_name
            break

    if ret_val is None and not clobber:
        # Since repositories file is cached, it can be that something has changed.
        # Adding clobber=True will make it overwrite the cached version with latest one.
        query_repo_name_from_buildername(buildername, clobber=True)

    if ret_val is None:
        raise MozciError("Repository name not found in buildername. "
                         "Please provide a correct buildername.")

    return ret_val


def query_repo_url_from_buildername(buildername):
    """Return the full repository URL for a given known buildername."""
    repo_name = query_repo_name_from_buildername(buildername)
    return repositories.query_repo_url(repo_name)


def query_revisions_range(repo_name, from_revision, to_revision):
    """Return a list of revisions for that range."""
    return pushlog.query_revisions_range(
        repositories.query_repo_url(repo_name),
        from_revision,
        to_revision,
    )


#
# Validation code
#
def valid_builder(buildername):
    """Determine if the builder you're trying to trigger is valid."""
    builders = query_builders()
    if buildername in builders:
        LOG.debug("Buildername %s is valid." % buildername)
        return True
    else:
        LOG.warning("Buildername %s is *NOT* valid." % buildername)
        LOG.info("Check the file we just created builders.txt for "
                 "a list of valid builders.")
        with open(path_to_file('builders.txt'), "wb") as fd:
            for b in sorted(builders):
                fd.write(b + "\n")

        return False


#
# Trigger functionality
#
def trigger_job(revision, buildername, times=1, files=None, dry_run=False,
                extra_properties=None, trigger_build_if_missing=True):
    """Trigger a job through self-serve.

    We return a list of all requests made.
    """
    repo_name = query_repo_name_from_buildername(buildername)
    builder_to_trigger = None
    list_of_requests = []
    repo_url = repositories.query_repo_url(repo_name)

    if VALIDATE and not pushlog.valid_revision(repo_url, revision):
        return list_of_requests

    LOG.info("===> We want to trigger '%s' on revision '%s' a total of %d time(s)." %
             (buildername, revision, times))
    LOG.info("")  # Extra line to help visual of logs

    if VALIDATE and not valid_builder(buildername):
        LOG.error("The builder %s requested is invalid" % buildername)
        # XXX How should we exit cleanly?
        exit(-1)

    if files:
        builder_to_trigger = buildername
        _all_urls_reachable(files)
    else:
        builder_to_trigger, files = determine_trigger_objective(
            revision=revision,
            buildername=buildername,
            trigger_build_if_missing=trigger_build_if_missing
        )

        if builder_to_trigger != buildername and times != 1:
            # The user wants to trigger a downstream job,
            # however, we need a build job instead.
            # We should trigger the downstream job multiple times, however,
            # we only trigger the upstream jobs once.
            LOG.debug("Since we need to trigger a build job we don't need to "
                      "trigger it %s times but only once." % times)
            if trigger_build_if_missing:
                LOG.info("In order to trigger %s %i times, "
                         "please run the script again after %s ends."
                         % (buildername, times, builder_to_trigger))
            else:
                LOG.info("We won't trigger '%s' because there is no working build."
                         % buildername)
                LOG.info("")
            times = 1

    if builder_to_trigger:
        if dry_run:
            LOG.info("Dry-run: We were going to request '%s' %s times." %
                     (builder_to_trigger, times))
            # Running with dry_run being True will only output information
            trigger(builder_to_trigger, revision, files, dry_run, extra_properties)
        else:
            for _ in range(times):
                req = trigger(builder_to_trigger, revision, files, dry_run, extra_properties)
                if req is not None:
                    list_of_requests.append(req)
    else:
        LOG.debug("Nothing needs to be triggered")

    # Cleanup old buildjson files.
    clean_directory()

    return list_of_requests


def trigger_range(buildername, revisions, times=1, dry_run=False,
                  files=None, extra_properties=None, trigger_build_if_missing=True):
    """Schedule the job named "buildername" ("times" times) in every revision on 'revisions'."""
    repo_name = query_repo_name_from_buildername(buildername)
    repo_url = repositories.query_repo_url(repo_name)

    if revisions != []:
        LOG.info("We want to have %s job(s) of %s on revisions %s" %
                 (times, buildername, str(revisions)))

    for rev in revisions:
        LOG.info("")
        LOG.info("=== %s ===" % rev)
        if VALIDATE and not pushlog.valid_revision(repo_url, rev):
            LOG.info("We can't trigger anything on pushes without a valid revision.")
            continue

        LOG.info("We want to have %s job(s) of %s on revision %s" %
                 (times, buildername, rev))

        # 1) How many potentially completed jobs can we get for this buildername?
        matching_jobs = QUERY_SOURCE.get_matching_jobs(repo_name, rev, buildername)
        successful_jobs, pending_jobs, running_jobs, _, failed_jobs = \
            _status_summary(matching_jobs)

        potential_jobs = pending_jobs + running_jobs + successful_jobs + failed_jobs
        # TODO: change this debug message when we have a less hardcoded _status_summary
        LOG.debug("We found %d pending/running jobs, %d successful jobs and "
                  "%d failed jobs" % (pending_jobs + running_jobs, successful_jobs, failed_jobs))

        if potential_jobs >= times:
            LOG.info("We have %d job(s) for '%s' which is enough for the %d job(s) we want." %
                     (potential_jobs, buildername, times))

        else:
            # 2) If we have less potential jobs than 'times' instances then
            #    we need to fill it in.
            LOG.info("We have found %d potential job(s) matching '%s' on %s. "
                     "We need to trigger more." % (potential_jobs, buildername, rev))

            # If a job matching what we want already exists, we can
            # use the retrigger API in self-serve to retrigger that
            # instead of creating a new arbitrary job
            if len(matching_jobs) > 0 and files is None:
                request_id = QUERY_SOURCE.get_buildapi_request_id(repo_name, matching_jobs[0])
                make_retrigger_request(
                    repo_name,
                    request_id,
                    count=(times - potential_jobs),
                    dry_run=dry_run)

            # If no matching job exists, we have to trigger a new arbitrary job
            else:
                list_of_requests = trigger_job(
                    revision=rev,
                    buildername=buildername,
                    times=(times - potential_jobs),
                    dry_run=dry_run,
                    files=files,
                    extra_properties=extra_properties,
                    trigger_build_if_missing=trigger_build_if_missing)

                if list_of_requests and any(req.status_code != 202 for req in list_of_requests):
                    LOG.warning("Not all requests succeeded.")

        # TODO:
        # 3) Once we trigger a build job, we have to monitor it to make sure that it finishes;
        #    at that point we have to trigger as many test jobs as we originally intended
        #    If a build job does not finish, we have to notify the user... what should it then
        #    happen?


def trigger(builder, revision, files=[], dry_run=False, extra_properties=None):
    """Helper to trigger a job.

    Returns a request.
    """
    global SCHEDULING_MANAGER
    sch_mgr = SCHEDULING_MANAGER

    if revision not in sch_mgr:
        sch_mgr[revision] = []

    sch_mgr[revision].append(builder)

    repo_name = query_repo_name_from_buildername(builder)
    return trigger_arbitrary_job(repo_name, builder, revision, files, dry_run,
                                 extra_properties)


def trigger_missing_jobs_for_revision(repo_name, revision, dry_run=False,
                                      trigger_build_if_missing=True):
    """
    Trigger missing jobs for a given revision.
    Jobs containing 'b2g' or 'pgo' in their buildername will not be triggered.
    """
    builders_for_repo = list_builders(repo_name=repo_name)

    for buildername in builders_for_repo:
        trigger_range(
            buildername=buildername,
            revisions=[revision],
            times=1,
            dry_run=dry_run,
            extra_properties={
                'mozci_request': {
                    'type': 'trigger_missing_jobs_for_revision'
                }
            },
            trigger_build_if_missing=trigger_build_if_missing
        )


def trigger_all_talos_jobs(repo_name, revision, times, dry_run=False):
    """
    Trigger talos jobs (excluding 'pgo') for a given revision.
    """
    pgo = False
    if repo_name in ['mozilla-central', 'mozilla-aurora', 'mozilla-beta']:
        pgo = True
    buildernames = build_talos_buildernames_for_repo(repo_name, pgo)
    for buildername in buildernames:
        trigger_range(buildername=buildername,
                      revisions=[revision],
                      times=times,
                      dry_run=dry_run,
                      extra_properties={'mozci_request': {
                                        'type': 'trigger_all_talos_jobs',
                                        'times': times}
                                        })


def manual_backfill(revision, buildername, max_revisions, dry_run=False):
    """
    This function is used to trigger jobs for a range of revisions
    when a user clicks the backfill icon for a job on Treeherder.

    It backfills to the last known job on Treeherder.
    """
    repo_url = query_repo_url_from_buildername(buildername)
    # We want to use data from treeherder for manual backfilling for long term.
    set_query_source("treeherder")
    revlist = pushlog.query_revisions_range_from_revision_before_and_after(
        repo_url=repo_url,
        revision=revision,
        before=max_revisions,
        after=-1)  # We do not want the current job in the revision to be included.
    filtered_revlist = _filter_backfill_revlist(buildername, revlist, only_successful=False)
    trigger_range(
        buildername=buildername,
        revisions=filtered_revlist,
        times=1,
        dry_run=dry_run,
        extra_properties={
            'mozci_request': {
                'type': 'manual_backfill',
                'builders': [buildername]}
            }
    )


def _filter_backfill_revlist(buildername, revisions, only_successful=False):
    """ Return list of revisions without good jobs for a given buildername based on an initial list.

    If a job is found (many states), we return a revision list up to the revision of
    that job (aka a sublist of *revisions*). If only_successful is passed we will only
    be happy with a successful state.

    If a job is **not** found, we will simply run trigger_range() of the complete list
    of revisions and notify the user.
    """
    new_revisions_list = []
    repo_name = query_repo_name_from_buildername(buildername)
    # XXX: We're asssuming that the list is ordered by the push_id
    LOG.info("We want to find a job for '%s' in this range: [%s:%s] (%d revisions)" %
             (buildername, revisions[0], revisions[-1], len(revisions)))
    for rev in revisions:
        matching_jobs = QUERY_SOURCE.get_matching_jobs(repo_name, rev, buildername)
        if not only_successful:
            successful, pending, running, _, failed = _status_summary(matching_jobs)
            if matching_jobs and (successful or pending or running or failed):
                LOG.info("We found a job for buildername '%s' on %s" %
                         (buildername, rev))
                # We don't need to look any further in the list of revisions
                break
            else:
                new_revisions_list.append(rev)
        else:
            successful_jobs = _status_summary(matching_jobs)[0]
            if successful_jobs > 0:
                LOG.info("The last successful job for buildername '%s' is on %s" %
                         (buildername, rev))
                # We don't need to look any further in the list of revisions
                break
            else:
                new_revisions_list.append(rev)

    LOG.debug("We only need to backfill %s" % new_revisions_list)
    return new_revisions_list


def find_backfill_revlist(buildername, revision, max_revisions):
    """Determine which revisions we need to trigger in order to backfill.

    This function is generally called by automatic backfilling on pulse_actions.
    We need to take into consideration that a job might not be run for many revisions
    due to SETA.  We also might have a permanent failure appear after a reconfiguration
    (a new job is added).

    When a permanent failure appears, we keep on adding load unnecessarily
    by triggering coalesced jobs in between pushes.

    Long lived failing job (it could be hidden):
    * push N   -> failed job
    * push N-1 -> failed/coalesced job
    * push N-2 -> failed/coalesced job
    ...
    * push N-max_revisions-1 -> failed/coalesced job

    If the list of revision we need to trigger is larger than max_revisions
    it means that we either have not had that job scheduled beyond max_revisions
    or it has been failing forever.
    """
    # XXX: There is a chance that a green job has run in a newer push (the priority was higher),
    # however, this is unlikely.

    # XXX: We might need to consider when a backout has already landed and stop backfilling
    LOG.info("BACKFILL-START:%s_%s begins." % (revision[0:8], buildername))

    revlist = pushlog.query_revisions_range_from_revision_before_and_after(
        repo_url=query_repo_url_from_buildername(buildername),
        revision=revision,
        before=max_revisions - 1,
        after=0
    )
    new_revlist = _filter_backfill_revlist(buildername, revlist, only_successful=True)

    if len(new_revlist) >= max_revisions:
        # It is likely that we are facing a long lived permanent failure
        LOG.debug("We're not going to backfill %s since it is likely to be a permanent "
                  "failure." % buildername)
        LOG.info("BACKFILL-END:%s_%s will not backfill." % (revision[0:8], buildername))
        return []
    else:
        LOG.info("BACKFILL-END:%s_%s will backfill %s." %
                 (revision[0:8], buildername, new_revlist))
        return new_revlist
