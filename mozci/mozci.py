"""
This module is generally your starting point.

In here, you will also find high level functions that will do various low level
interactions with distinct modules to meet your needs.
"""
from __future__ import absolute_import

import logging

from buildapi_client import (
    BuildapiDown,
    make_retrigger_request,
    trigger_arbitrary_job
)

from mozci import repositories
from mozci.errors import (
    BuildjsonError,
    MozciError,
)
from mozci.platforms import (
    build_talos_buildernames_for_repo,
    get_builder_extra_properties,
    get_max_pushes,
    determine_upstream_builder,
    is_downstream,
    is_upstream,
    list_builders,
    get_talos_jobs_for_build,
)
from mozci.sources import buildjson
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
    TreeherderApi,
    status_to_string,
)
from mozci.utils.authentication import get_credentials
from mozci.utils.misc import _all_urls_reachable
from mozci.utils.transfer import clean_directory
from mozhginfo.pushlog_client import (
    query_push_by_revision,
    query_pushes_by_specified_revision_range,
    query_pushes_by_revision_range,
    valid_revision,
)
from requests.exceptions import (
    ConnectionError,
    ReadTimeout
)

LOG = logging.getLogger('mozci')
SCHEDULING_MANAGER = {}

# Default value of QUERY_SOURCE
QUERY_SOURCE = BuildApi()

# Set this value to False in your tool to prevent any sort of validation
VALIDATE = True


def disable_validations():
    ''' This disables validating if builders are valid '''
    global VALIDATE
    if VALIDATE:
        LOG.debug("Disabling validations.")
        VALIDATE = False


def validate():
    return VALIDATE


def set_query_source(query_source="buildapi"):
    """ Function to set the global QUERY_SOURCE """
    global QUERY_SOURCE
    assert query_source in ('buildapi', 'treeherder')
    LOG.info('Setting {} as our query source'.format(query_source))
    if query_source == "treeherder":
        source_class = TreeherderApi
    else:
        source_class = BuildApi
    QUERY_SOURCE = source_class()


def _unique_build_request(buildername, revision):
    """ Prevent scheduling the same build more than once."""
    if is_upstream(buildername) and \
       revision in SCHEDULING_MANAGER and \
       buildername in SCHEDULING_MANAGER[revision]:
        LOG.info("We have already scheduled the build '%s' for "
                 "revision %s during this session. We don't allow "
                 "multiple requests." % (buildername, revision))
        return False
    else:
        return True


def _add_builder_to_scheduling_manager(revision, buildername):
    global SCHEDULING_MANAGER

    if revision not in SCHEDULING_MANAGER:
        SCHEDULING_MANAGER[revision] = []

    SCHEDULING_MANAGER[revision].append(buildername)


class StatusSummary(object):
    """class which represent the summary of status"""
    def __init__(self, jobs):
        assert type(jobs) == list
        self._successful = 0
        self._pending = 0
        self._running = 0
        self._coalesced = 0
        self._failed = 0
        for job in jobs:
            status = QUERY_SOURCE.get_job_status(job)
            if status == PENDING:
                self._pending += 1
            if status in (RUNNING, UNKNOWN):
                self._running += 1
            if status == SUCCESS:
                self._successful += 1
            if status == COALESCED:
                self._coalesced += 1
            if status in (FAILURE, WARNING, EXCEPTION, RETRY):
                self._failed += 1

    @property
    def successful_jobs(self):
        return self._successful

    @property
    def pending_jobs(self):
        return self._pending

    @property
    def running_jobs(self):
        return self._running

    @property
    def coalesced_jobs(self):
        return self._coalesced

    @property
    def failed_jobs(self):
        return self._failed

    @property
    def potential_jobs(self):
        return self._successful + self._pending + self._running + self._failed


def determine_trigger_objective(revision, buildername,
                                trigger_build_if_missing=True,
                                will_use_buildapi=False):
    """Determine builder to trigger and files if needed.
    If a downstream builder needs the parent to be trigger we return
    the parent builder name and any files if needed when scheduling.

    Returns:
    * The name of the builder we need to trigger
    * Files, if needed, to trigger such builder

    """
    # Upstream builders return their ownself
    build_buildername = determine_upstream_builder(buildername)

    if build_buildername is None:
        LOG.info("We believe {} is a builder triggered via Buildbot bridge "
                 "and we won't schedule anything.".format(buildername))
        return None, None, None

    builder_to_trigger = None
    files = None
    repo_name = query_repo_name_from_buildername(buildername)

    if VALIDATE and not valid_builder(build_buildername):
        raise MozciError("Our platforms mapping system has failed.")

    if build_buildername == buildername:
        # For a build job we know that we don't need files to
        # trigger it and it's the build job we want to trigger
        return build_buildername, None, None

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
        except BuildjsonError:
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
                      "non-existent.")
            continue

        # Successful or failed jobs may have the files we need
        # Bug 1314930 - TreeherderApi() cannot always reach for the files
        files = _find_files(job)

        if not files or not _all_urls_reachable(files.values()):
            LOG.debug("We can't determine the files for this build or "
                      "can't reach them.")
            files = None
        else:
            working_job = job
            break

        LOG.info("We found a job that finished, however, it did not produced files.")
        LOG.info("Status of job: {}".format(status_to_string(status)))
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
            if will_use_buildapi:
                LOG.info("We will trigger 1) '%s'" % build_buildername)
                LOG.info("instead of 2) '%s'" % buildername)
                LOG.info("We need to trigger the build job once (1) "
                         "in order to be able to run the test job (2).")
                if repo_name == 'try':
                    LOG.info("You'll need to run the script again after (1) is done to "
                             "trigger (2).")
                else:
                    LOG.info("After (1) is done and if no coalesccing happens the test "
                             "jobs associated with it will be triggered.")
            builder_to_trigger = build_buildername

    if files:
        return builder_to_trigger, files['packageUrl'], files['testsUrl']
    else:
        return builder_to_trigger, None, None


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
    files = {}

    job_status = _status_info(job_schedule_info)

    if job_status is None:
        LOG.warning("We should not have received an empty status")
        return files

    properties = job_status.get("properties")

    if not properties:
        LOG.error(str(job_status))
        raise MozciError("The status of the job is expected to have a "
                         "properties key, however, it is missing.")

    LOG.debug("We want to find the files needed to trigger %s" %
              properties["buildername"])

    # We need the packageUrl, and one of testsUrl and testPackagesUrl,
    # preferring testPackagesUrl.
    if 'packageUrl' in properties:
        files['packageUrl'] = properties['packageUrl']

    if 'testPackagesUrl' in properties:
        files['testsUrl'] = properties['testPackagesUrl']
    elif 'testsUrl' in properties:
        files['testsUrl'] = properties['testsUrl']

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
    return query_pushes_by_revision_range(
        repo_url=repositories.query_repo_url(repo_name),
        from_revision=from_revision,
        to_revision=to_revision,
        return_revision_list=True
    )


#
# Validation code
#
def valid_builder(buildername, quiet=False):
    """Determine if the builder you're trying to trigger is valid."""
    builders = query_builders()
    if buildername in builders:
        LOG.debug("Buildername %s is valid." % buildername)
        return True
    else:
        if not quiet:
            LOG.warning("Buildername %s is *NOT* valid." % buildername)
            LOG.info("Check {} for valid builders.".format(
                'http://people.mozilla.org/~armenzg/permanent/all_builders.txt')
            )

        return False


#
# Trigger functionality
#
def trigger_job(revision, buildername, times=1, files=None, dry_run=False,
                extra_properties={}, trigger_build_if_missing=True):
    """Trigger a job through self-serve.

    We return a list of all requests made.
    """
    if not extra_properties:
        extra_properties = {}
    extra_properties.update(get_builder_extra_properties(buildername))

    repo_name = query_repo_name_from_buildername(buildername)
    builder_to_trigger = None
    list_of_requests = []
    repo_url = repositories.query_repo_url(repo_name)
    if len(revision) != 40:
        LOG.info('We are going to convert the revision into 40 chars ({}).'.format(revision))
        push_info = query_push_by_revision(repo_url, revision)
        revision = push_info.changesets[0].node
        assert len(revision) == 40, 'This should have been a 40 char revision.'

    if VALIDATE and not valid_revision(repo_url, revision):
        return list_of_requests

    LOG.info("==> We want to trigger '%s' a total of %d time(s)." % (buildername, times))

    if VALIDATE and not valid_builder(buildername):
        LOG.error("The builder %s requested is invalid" % buildername)
        # XXX How should we exit cleanly?
        exit(-1)

    if files:
        builder_to_trigger = buildername
        _all_urls_reachable(files)
    else:
        builder_to_trigger, package_url, test_url = determine_trigger_objective(
            revision=revision,
            buildername=buildername,
            trigger_build_if_missing=trigger_build_if_missing,
            will_use_buildapi=True
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
            trigger(
                builder=builder_to_trigger,
                revision=revision,
                files=[package_url, test_url],
                dry_run=dry_run,
                extra_properties=extra_properties
            )
        else:
            for _ in range(times):
                req = trigger(
                    builder=builder_to_trigger,
                    revision=revision,
                    files=[package_url, test_url],
                    dry_run=dry_run,
                    extra_properties=extra_properties
                )
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
        LOG.info("We want to have %s job(s) of %s on the following revisions: "
                 % (times, buildername))
        for r in revisions:
            LOG.info(" - %s" % r)

    for rev in revisions:
        LOG.info("")
        LOG.info("=== %s ===" % rev)
        if VALIDATE and not valid_revision(repo_url, rev):
            LOG.info("We can't trigger anything on pushes without a valid revision.")
            continue

        # 1) How many potentially completed jobs can we get for this buildername?
        matching_jobs = QUERY_SOURCE.get_matching_jobs(repo_name, rev, buildername)
        status_summary = StatusSummary(matching_jobs)

        # TODO: change this debug message when we have a less hardcoded _status_summary
        LOG.debug("We found %d pending/running jobs, %d successful jobs and "
                  "%d failed jobs" % (status_summary.pending_jobs + status_summary.running_jobs,
                                      status_summary.successful_jobs, status_summary.failed_jobs))

        if status_summary.potential_jobs >= times:
            LOG.info("We have %d job(s) for '%s' which is enough for the %d job(s) we want." %
                     (status_summary.potential_jobs, buildername, times))

        else:
            # 2) If we have less potential jobs than 'times' instances then
            #    we need to fill it in.
            LOG.info("We have found %d potential job(s) matching '%s' on %s. "
                     "We need to trigger more." % (status_summary.potential_jobs, buildername, rev))

            schedule_new_job = True
            # If a job matching what we want already exists, we can
            # use the retrigger API in self-serve to retrigger that
            # instead of creating a new arbitrary job
            if len(matching_jobs) > 0 and files is None:
                try:
                    request_id = QUERY_SOURCE.get_buildapi_request_id(repo_name, matching_jobs[0])
                    make_retrigger_request(
                        repo_name=repo_name,
                        request_id=request_id,
                        auth=get_credentials(),
                        count=(times - status_summary.potential_jobs),
                        dry_run=dry_run)
                    schedule_new_job = False
                except (IndexError, ConnectionError, ReadTimeout, ValueError) as e:
                    # Logging until we can determine why we get these errors
                    # We should have one of these:
                    # {'requests': [{'request_id': int]}
                    # {'request_id': int}
                    LOG.info(matching_jobs[0])
                    LOG.info(str(e))
                    LOG.warning(
                        "We failed to retrigger the job, however, "
                        "we will try to schedule a new one."
                    )

            # If no matching job exists, we have to trigger a new arbitrary job
            if schedule_new_job:
                list_of_requests = trigger_job(
                    revision=rev,
                    buildername=buildername,
                    times=(times - status_summary.potential_jobs),
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


def trigger(builder, revision, files=None, dry_run=False, extra_properties=None):
    """Helper to trigger a job.

    Returns a request.
    """
    _add_builder_to_scheduling_manager(revision=revision, buildername=builder)

    repo_name = query_repo_name_from_buildername(builder)

    if is_downstream(builder) and not files:
        raise MozciError('We have requested to trigger a test job, however, we have not provided '
                         'which files to run against.')

    return trigger_arbitrary_job(repo_name=repo_name,
                                 builder=builder,
                                 revision=revision,
                                 auth=get_credentials(),
                                 files=files,
                                 dry_run=dry_run,
                                 extra_properties=extra_properties)


def trigger_talos_jobs_for_build(buildername, revision, times, dry_run=False):
    """
    Trigger all talos jobs for a given build and revision.
    """
    LOG.info('Trigger all talos jobs for {} on {}'.format(buildername, revision))
    failed_builders = ''
    buildernames = get_talos_jobs_for_build(buildername)
    for buildername in buildernames:
        try:
            trigger_job(
                revision=revision,
                buildername=buildername,
                times=times,
                dry_run=dry_run
            )
        except BuildapiDown:
            LOG.exception('Buildapi is down. We will not try anymore.')
            return FAILURE
        except:
            LOG.exception('We failed to trigger {}; Let us try the rest.'.format(buildername))
            failed_builders += '%s\n' % buildername

    if failed_builders:
        LOG.info("Here's the list of builders that did not get scheduled:\n"
                 "{}".format(failed_builders))
        return FAILURE

    return SUCCESS


def trigger_all_talos_jobs(repo_name, revision, times, priority=0, dry_run=False):
    """
    Trigger talos jobs (excluding 'pgo') for a given revision.
    """
    LOG.info('Trigger all talos jobs for {}/{}'.format(repo_name, revision))
    pgo = False
    if repo_name in ['mozilla-central', 'mozilla-aurora', 'mozilla-beta']:
        pgo = True
    buildernames = build_talos_buildernames_for_repo(repo_name, pgo)
    for buildername in buildernames:
        trigger_job(buildername=buildername,
                    revision=revision,
                    times=times,
                    dry_run=dry_run,
                    trigger_build_if_missing=True,
                    extra_properties={
                        'mozci_request': {
                            'type': 'trigger_all_talos_jobs',
                            'times': times,
                            'priority': priority
                        }
                    })


def manual_backfill(revision, buildername, dry_run=False):
    """
    This function is used to trigger jobs for a range of revisions
    when a user clicks the backfill icon for a job on Treeherder.

    It backfills to the last known job on Treeherder.
    """
    factor = 1.5
    seta_skip = get_max_pushes(buildername)
    # Use SETA's skip pushes times factor
    max_pushes = seta_skip * factor
    repo_url = query_repo_url_from_buildername(buildername)
    # We want to use data from treeherder for manual backfilling for long term.
    set_query_source("treeherder")

    revlist = query_pushes_by_specified_revision_range(
        repo_url=repo_url,
        revision=revision,
        before=max_pushes,
        after=-1,  # We don't want the current job in the revision to be included.
        return_revision_list=True)

    LOG.info("We're *aiming* to backfill; note that we ignore the revision that you request "
             "to backfill from ({}) up to {} pushes (seta skip: {}; factor: {}) "
             "and we backfill up to the last green if found.".format(
                 revision[:12], max_pushes, seta_skip, factor))
    LOG.info("https://treeherder.mozilla.org/#/jobs?repo={}&filter-searchStr={}"
             "&tochange={}&fromchange={}".format(
                 repo_url.split('/')[-1],
                 buildername,
                 revlist[-1],
                 revlist[0],
             ))

    filtered_revlist = revlist
    # Talos jobs are generally always green and we want to fill in all holes in a range
    if 'talos' not in buildername:
        filtered_revlist = _filter_backfill_revlist(buildername, list(reversed(revlist)),
                                                    only_successful=True)

    if len(filtered_revlist) == 0:
        LOG.info("We don't have a revision list to work with.")
        return

    if len(revlist) != len(filtered_revlist):
        LOG.info("NOTICE: We were aiming for a revlist of {}, however, we only "
                 "need to backfill {} revisions".format(len(revlist), len(filtered_revlist)))

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
             (buildername, revisions[0][:12], revisions[-1][:12], len(revisions)))

    for rev in revisions:
        matching_jobs = QUERY_SOURCE.get_matching_jobs(repo_name, rev, buildername)
        if not only_successful:
            status_summary = StatusSummary(matching_jobs)
            if matching_jobs and (status_summary.successful_jobs or status_summary.pending_jobs or
                                  status_summary.running_jobs or status_summary.failed_jobs):
                LOG.info("We found a job for buildername '%s' on %s" %
                         (buildername, rev))
                # We don't need to look any further in the list of revisions
                break
            else:
                new_revisions_list.append(rev)
        else:
            successful_jobs = StatusSummary(matching_jobs).successful_jobs
            if successful_jobs > 0:
                LOG.info("The last successful job for buildername '%s' is on %s" %
                         (buildername, rev))
                # We don't need to look any further in the list of revisions
                break
            else:
                new_revisions_list.append(rev)

    LOG.debug("We only need to backfill %s" % new_revisions_list)
    return new_revisions_list


def find_backfill_revlist(buildername, revision, max_pushes=None):
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
    * push N-max_pushes-1 -> failed/coalesced job

    If the list of revision we need to trigger is larger than max_pushes
    it means that we either have not had that job scheduled beyond max_pushes
    or it has been failing forever.
    """
    max_pushes = max_pushes if max_pushes is not None else get_max_pushes(buildername)
    # XXX: There is a chance that a green job has run in a newer push (the priority was higher),
    # however, this is unlikely.

    # XXX: We might need to consider when a backout has already landed and stop backfilling
    LOG.info("BACKFILL-START:%s_%s begins." % (revision[0:8], buildername))

    revlist = query_pushes_by_specified_revision_range(
        repo_url=query_repo_url_from_buildername(buildername),
        revision=revision,
        before=max_pushes - 1,
        after=0,
        return_revision_list=True
    )
    new_revlist = _filter_backfill_revlist(buildername, revlist, only_successful=True)

    if len(new_revlist) >= max_pushes:
        # It is likely that we are facing a long lived permanent failure
        LOG.debug("We're not going to backfill %s since it is likely to be a permanent "
                  "failure." % buildername)
        LOG.info("BACKFILL-END:%s_%s will not backfill." % (revision[0:8], buildername))
        return []
    else:
        LOG.info("BACKFILL-END:%s_%s will backfill %s." %
                 (revision[0:8], buildername, new_revlist))
        return new_revlist
