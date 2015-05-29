"""
This module is generally your starting point.

Instead of accesing directly a module that represents a data source
(e.g. buildapi.py), we highly encourage you to use mozci.py instead which
interfaces with them through.  As the continuous integration changes,
you will be better off letting mozci.py determine which source to reach
to take the actions you need.

In here, you will also find high level functions that will do various low level
interactions with distinct modules to meet your needs.
"""
from __future__ import absolute_import

import logging

from mozci.platforms import determine_upstream_builder, is_downstream
from mozci.sources import allthethings, buildapi, buildjson, pushlog
from mozci.utils.misc import _all_urls_reachable
from mozci.utils.transfer import path_to_file

LOG = logging.getLogger('mozci')
SCHEDULING_MANAGER = {}


def _matching_jobs(buildername, all_jobs):
    """Return all jobs that matched the criteria."""
    LOG.debug("Find jobs matching '%s'" % buildername)
    matching_jobs = []
    for j in all_jobs:
        if j["buildername"] == buildername:
            matching_jobs.append(j)

    LOG.debug("We have found %d job(s) of '%s'." %
              (len(matching_jobs), buildername))
    return matching_jobs


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
            LOG.info("We have already scheduled the build '%s' for "
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

    for job in jobs:
        status = buildapi.query_job_status(job)
        if status == buildapi.PENDING:
            pending += 1
        if status == buildapi.RUNNING:
            running += 1
        if status == buildapi.SUCCESS:
            successful += 1
        if status == buildapi.COALESCED:
            coalesced += 1

    return (successful, pending, running, coalesced)


def _determine_trigger_objective(revision, buildername):
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

    assert valid_builder(build_buildername), \
        "Our platforms mapping system has failed."

    if build_buildername == buildername:
        # For a build job we know that we don't need files to
        # trigger it and it's the build job we want to trigger
        return build_buildername, None

    # Let's figure out which jobs are associated to such revision
    all_jobs = query_jobs(repo_name, revision)
    # Let's only look at jobs that match such build_buildername
    build_jobs = _matching_jobs(build_buildername, all_jobs)

    # We need to determine if we need to trigger a build job
    # or the test job
    working_job = None
    running_job = None
    failed_job = None

    LOG.debug("List of matching jobs:")
    for job in build_jobs:
        # Successful, running and failed jobs may have the files we need
        files = _find_files(job)
        if files != [] and _all_urls_reachable(files):
            working_job = job
            break
        else:
            LOG.debug("We can't determine the files for this build or "
                      "can't reach them.")
            files = None

        try:
            status = buildapi.query_job_status(job)
        except buildjson.BuildjsonException:
            LOG.debug("We have hit bug 1159279 and have to work around it. We will pretend that "
                      "we could not reach the files for it.")
            continue

        if status == buildapi.RUNNING:
            LOG.debug("We found a running build job. We don't search anymore.")
            running_job = job

        else:
            LOG.info("We found a job that finished but its status "
                     "is not successful. status: %d" % status)
            failed_job = job

    if working_job:
        # We found a build job with the necessary files. It could be a
        # successful job, a running job that already emitted files or a
        # testfailed job
        LOG.debug(str(working_job))
        LOG.info("We have the necessary files to trigger the downstream job.")
        # We have the files needed to trigger the test job
        builder_to_trigger = buildername
    elif running_job:
        LOG.info("We found a running build job without files. We will not trigger another one. "
                 "You have to run the script again after the build job is finished to trigger %s." %
                 buildername)
        builder_to_trigger = None
    elif failed_job:
        LOG.info("The build job %s failed on revision %s without generating the necessary files. "
                 "We will not trigger anything." % (build_buildername, revision))
        builder_to_trigger = None
    else:
        # We were trying to build a test job, however, we determined
        # that we need an upstream builder instead
        if not _unique_build_request(build_buildername, revision):
            # This is a safeguard to prevent triggering a build
            # job multiple times if it is not intentional
            builder_to_trigger = None
        else:
            LOG.info("We will trigger 1) '%s' instead of 2) '%s'" % (build_buildername, buildername))
            LOG.info("We need to trigger the build job once (1) in order to be able to run the test job (2).")
            if repo_name == 'try':
                LOG.info("You'll need to run the script again after (1) is done to trigger (2).")
            else:
                LOG.info("After (1) is done every test job associated with it will be triggered.")
            builder_to_trigger = build_buildername

    return builder_to_trigger, files


def _status_info(job_schedule_info):
    # Let's grab the last job
    complete_at = job_schedule_info["requests"][0]["complete_at"]
    request_id = job_schedule_info["requests"][0]["request_id"]

    # NOTE: This call can take a bit of time
    return buildjson.query_job_data(complete_at, request_id)


def _find_files(job_schedule_info):
    """Find the files needed to trigger a job."""
    files = []

    job_status = _status_info(job_schedule_info)
    assert job_status is not None, \
        "We should not have received an empty status"

    properties = job_status.get("properties")

    if not properties:
        LOG.error(str(job_status))
        raise Exception("The status of the job is expected to have a "
                        "properties key, however, it is missing.")

    LOG.debug("We want to find the files needed to trigger %s" %
              properties["buildername"])

    if "packageUrl" in properties:
        files.append(properties["packageUrl"])
    if "testsUrl" in properties:
        files.append(properties["testsUrl"])

    return files


#
# Query functionality
#
def query_jobs(repo_name, revision):
    """Return list of jobs scheduling information for a revision."""
    return buildapi.query_jobs_schedule(repo_name, revision)


def query_jobs_buildername(buildername, revision):
    """Return **status** information for a buildername on a given revision."""
    # NOTE: It's unfortunate that there is scheduling and status data.
    #       I think we might need to remove this distinction for the user's
    #       sake.
    status_info = []
    repo_name = query_repo_name_from_buildername(buildername)
    all_jobs = buildapi.query_jobs_schedule(repo_name, revision)
    jobs = _matching_jobs(buildername, all_jobs)
    # The user wants the status data rather than the scheduling data
    for job_schedule_info in jobs:
        status_info.append(_status_info(job_schedule_info))

    return status_info


def query_jobs_schedule_url(repo_name, revision):
    """Return URL of where a developer can login to see the scheduled jobs for a revision."""
    return buildapi.query_jobs_url(repo_name, revision)


def query_builders():
    """Return list of all builders."""
    return allthethings.list_builders()


def query_repo_name_from_buildername(buildername, clobber=False):
    """Return the repository name from a given buildername."""
    repositories = buildapi.query_repositories(clobber)
    ret_val = None
    for repo_name in repositories:
        if (' %s ' % repo_name) in buildername:
            ret_val = repo_name
            break

    if ret_val is None and not clobber:
        # Since repositories file is cached, it can be that something has changed.
        # Adding clobber=True will make it overwrite the cached version with latest one.
        query_repo_name_from_buildername(buildername, clobber=True)

    if ret_val is None:
        raise Exception("Repository name not found in buildername. "
                        "Please provide a correct buildername.")

    return ret_val


def query_repositories():
    """Return all information about the repositories we have."""
    return buildapi.query_repositories()


def query_repository(repo_name):
    """Return all information about a specific repository."""
    return buildapi.query_repository(repo_name)


def query_repo_url_from_buildername(buildername):
    """Return the full repository URL for a given known buildername."""
    repo_name = query_repo_name_from_buildername(buildername)
    return buildapi.query_repo_url(repo_name)


def query_repo_url(repo_name):
    """Return the full repository URL for a given known repo_name."""
    return buildapi.query_repo_url(repo_name)


def query_revisions_range(repo_name, from_revision, to_revision):
    """Return a list of revisions for that range."""
    return pushlog.query_revisions_range(
        query_repo_url(repo_name),
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
                extra_properties=None, existing_only=False):
    """Trigger a job through self-serve.

    We return a list of all requests made.
    """
    repo_name = query_repo_name_from_buildername(buildername)
    builder_to_trigger = None
    list_of_requests = []
    LOG.info("We want to trigger '%s' on revision '%s' a total of %d time(s)." %
             (buildername, revision, times))

    if not buildapi.valid_revision(repo_name, revision):
        return list_of_requests

    if not valid_builder(buildername):
        LOG.error("The builder %s requested is invalid" % buildername)
        # XXX How should we exit cleanly?
        exit(-1)

    if files:
        builder_to_trigger = buildername
        _all_urls_reachable(files)
    else:
        builder_to_trigger, files = _determine_trigger_objective(
            revision,
            buildername,
        )

        if existing_only and (builder_to_trigger != buildername):
            LOG.info("We won't trigger %s because there is no working build."
                     % buildername)
            LOG.info("")
            return

        if builder_to_trigger != buildername and times != 1:
            # The user wants to trigger a downstream job,
            # however, we need a build job instead.
            # We should trigger the downstream job multiple times, however,
            # we only trigger the upstream jobs once.
            LOG.debug("Since we need to trigger a build job we don't need to "
                      "trigger it %s times but only once." % times)
            LOG.info("In order to trigger %s %i times, please run the script again after %s ends."
                     % (buildername, times, builder_to_trigger))
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

    return list_of_requests


def trigger_range(buildername, revisions, times=1, dry_run=False, files=None):
    """
    Schedule the job named "buildername" ("times" times) from "start_revision" to
    "end_revision".
    """
    repo_name = query_repo_name_from_buildername(buildername)
    LOG.info("We want to have %s job(s) of %s on revisions %s" %
             (times, buildername, str(revisions)))
    for rev in revisions:
        LOG.info("")
        LOG.info("=== %s ===" % rev)
        if not buildapi.valid_revision(repo_name, rev):
            LOG.info("We can't trigger anything on pushes that the revision is not valid for "
                     "buildapi.")
            continue

        LOG.info("We want to have %s job(s) of %s on revision %s" %
                 (times, buildername, rev))

        # 1) How many potentially completed jobs can we get for this buildername?
        jobs = query_jobs(repo_name, rev)
        matching_jobs = _matching_jobs(buildername, jobs)
        successful_jobs, pending_jobs, running_jobs = _status_summary(matching_jobs)[0:3]

        potential_jobs = pending_jobs + running_jobs + successful_jobs
        LOG.debug("We found %d pending jobs, %d running jobs and %d successful_jobs." %
                  (pending_jobs, running_jobs, successful_jobs))

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
            if len(matching_jobs) > 0:
                request_id = matching_jobs[0]["requests"][0]["request_id"]
                buildapi.make_retrigger_request(
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
                    files=files)

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
    return buildapi.trigger_arbitrary_job(repo_name, builder, revision, files, dry_run,
                                          extra_properties)


def backfill_revlist(buildername, revisions, times=1, dry_run=False):
    """
    Find the last known good job for that buildername iterating through the list of revisions.

    If a good job is found, we will only trigger_range() up to that revision instead of the
    complete list (subset of *revlist*).

    If a good job is **not** found, we will simply run trigger_range() of the complete list
    of revisions and notify the user.
    """
    new_revisions_list = []
    repo_name = query_repo_name_from_buildername(buildername)
    LOG.info("We want to find a successful job for '%s' in this range: [%s:%s]" %
             (buildername, revisions[0], revisions[-1]))
    for rev in revisions:
        jobs = query_jobs(repo_name, rev)
        matching_jobs = _matching_jobs(buildername, jobs)
        successful_jobs = _status_summary(matching_jobs)[0]
        if successful_jobs > 0:
            LOG.info("The last succesful job for buildername '%s' is on %s" %
                     (buildername, rev))
            # We don't need to look any further in the list of revisions
            break
        else:
            new_revisions_list.append(rev)

    LOG.info("We only need to backfill %s" % new_revisions_list)
    return new_revisions_list
