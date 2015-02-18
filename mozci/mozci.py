""" This module is generally your first starting point.
Instead of going directly to the module that represent different data sources
(e.g. buildapi.py), we highly encourage you to interface to them through here.
As the continuous integration changes, you will be better off letting mozci.py
determine which source to reach to take the actions you need.

In here, you will also find high level functions that will do various low level
interactions with distinct modules to meet your needs."""
import json
import logging
# import time

import platforms
from sources import allthethings, buildapi, buildjson, pushlog
from utils.misc import _all_urls_reachable
from utils.authentication import get_credentials

LOG = logging.getLogger()
AUTH = get_credentials()


def _matching_jobs(buildername, all_jobs):
    '''
    It returns all jobs that matched the criteria.
    '''
    LOG.debug("Find jobs matching '%s'" % buildername)
    matching_jobs = []
    for j in all_jobs:
        if j["buildername"] == buildername:
            matching_jobs.append(j)

    LOG.debug("We have matched %d jobs." % len(matching_jobs))
    return matching_jobs


def _determine_trigger_objective(repo_name, revision, buildername):
    '''
    Determine if we need to trigger any jobs and which job.

    trigger:  The name of the builder we need to trigger
    files:    Files needed for such builder
    '''
    trigger = None
    files = None

    # Let's figure out the associated build job
    # XXX: We have to handle the case when we query a build job
    build_buildername = platforms.associated_build_job(buildername, repo_name)
    assert valid_builder(build_buildername), \
        "Our platforms mapping system has failed."
    # Let's figure out which jobs are associated to such revision
    all_jobs = query_jobs(repo_name, revision)
    # Let's only look at jobs that match such build_buildername
    matching_jobs = _matching_jobs(build_buildername, all_jobs)

    if len(matching_jobs) == 0:
        # We need to simply trigger a build job
        LOG.debug("We are going to trigger %s instead of %s" %
                  (build_buildername, buildername))
        trigger = build_buildername
    else:
        # We know there is at leat one build job in some state
        # We need to determine if we need to trigger a build job
        # or the test job
        successful_job = None
        running_job = None

        LOG.debug("List of matching jobs:")
        for job in matching_jobs:
            LOG.debug(job)
            status = job.get("status")
            if status is None:
                LOG.debug("We found a running job. We don't search anymore.")
                running_job = job
                # XXX: If we break, we mean that we wait for this job and ignore
                # what status other jobs might be in
                break
            elif status == 0:
                LOG.debug("We found a successful job. We don't search anymore.")
                successful_job = job
                break
            else:
                LOG.debug("We found a job that finished but its status "
                          "is not successful.")

        if successful_job:
            # A build job has completed successfully
            # If the files are still around on FTP we can then trigger
            # the test job, otherwise, we need to trigger the build.
            LOG.debug("There is a job that has completed successfully.")
            LOG.debug(str(successful_job))
            files = _find_files(successful_job)
            if not _all_urls_reachable(files, AUTH):
                LOG.debug("The files are not around on Ftp anymore:")
                LOG.debug(files)
                trigger = build_buildername
                files = []
            else:
                # We have the files needed to trigger the test job
                trigger = buildername
        elif running_job:
            LOG.debug("We are waiting for a build to finish.")
            LOG.debug(str(running_job))
            trigger = None
        else:
            LOG.debug("We are going to trigger %s instead of %s" %
                      (build_buildername, buildername))
            trigger = build_buildername

    return trigger, files


def _find_files(scheduled_job_info):
    '''
    This function helps us find the files needed to trigger a job.
    '''
    files = []

    # Let's grab the last job
    complete_at = scheduled_job_info["requests"][0]["complete_at"]
    request_id = scheduled_job_info["requests"][0]["request_id"]

    # NOTE: This call can take a bit of time
    job_status = buildjson.query_job_data(complete_at, request_id)
    assert job_status is not None, \
        "We should not have received an empty status"

    properties = job_status.get("properties")

    if not properties:
        LOG.error(str(job_status))
        raise Exception("The status of the job is expected to have a "
                        "properties key, hwoever, it is missing.")

    LOG.debug("We want to find the files needed to trigger %s" %
              properties["buildername"])

    if properties:
        if "packageUrl" in properties:
            files.append(properties["packageUrl"])
        if "testsUrl" in properties:
            files.append(properties["testsUrl"])

    return files


#
# Query functionality
#
def query_jobs(repo_name, revision):
    '''
    Return list of jobs scheduling information for a revision.

    See buildapi.query_jobs_schedule for status information.
    '''
    # Comment out until we have optimizations to make
    # push_time = pushlog.query_changeset(query_repo_url(repo_name), revision)["date"]
    # now = int(time.time())
    # minutes_ago = (now - push_time) / 60
    # LOG.debug("The revision %s was pushed %s minutes ago." %
    #          (revision, minutes_ago))

    return buildapi.query_jobs_schedule(repo_name, revision, AUTH)


def query_jobs_schedule_url(repo_name, revision):
    ''' Returns url of where a developer can login to see the
        scheduled jobs for a revision.
    '''
    return buildapi.query_jobs_url(repo_name, revision)


def query_builders():
    ''' Returns list of all builders.
    '''
    return allthethings.list_builders()


def query_repositories():
    ''' Returns all information about the repositories we have.
    '''
    return buildapi.query_repositories(AUTH)


def query_repository(repo_name):
    ''' Returns all information about a specific repository.
    '''
    return buildapi.query_repository(repo_name, AUTH)


def query_repo_url(repo_name):
    ''' Returns the full repository URL for a given known repo_name.
    '''
    LOG.debug("Determine repository associated to %s" % repo_name)
    return query_repository(repo_name)["repo"]


def query_revisions_range(repo_name, start_revision, end_revision, version=2):
    ''' Return a list of revisions for that range.
    '''
    return pushlog.query_revisions_range(
        query_repo_url(repo_name),
        start_revision,
        end_revision,
        version
    )


#
# Validation code
#
def valid_builder(buildername):
    ''' This function determines if the builder you're trying to trigger is
    valid.
    '''
    builders = query_builders()
    if buildername in builders:
        LOG.debug("Buildername %s is valid." % buildername)
        return True
    else:
        LOG.warning("Buildername %s is *NOT* valid." % buildername)
        LOG.info("Check the file we just created builders.txt for "
                 "a list of valid builders.")
        with open("builders.txt", "wb") as fd:
            for b in sorted(builders):
                fd.write(b + "\n")

        return False


#
# Trigger functionality
#
def trigger_job(repo_name, revision, buildername, times=1, files=None, dry_run=False):
    ''' This function triggers a job through self-serve '''
    trigger = None
    list_of_requests = []
    LOG.debug("We want to trigger '%s' on revision '%s' a total of %d times." %
              (buildername, revision, times))

    if not valid_builder(buildername):
        LOG.error("The builder %s requested is invalid" % buildername)
        # XXX How should we exit cleanly?
        exit(-1)

    if files:
        trigger = buildername
        _all_urls_reachable(files, AUTH)
    else:
        # XXX: We should not need this if clause
        if platforms.does_builder_need_files(buildername):
            # For test and talos jobs we need to determine
            # what installer and test urls to use.
            # If there are no available files we might need to trigger
            # a build job instead
            trigger, files = _determine_trigger_objective(
                repo_name,
                revision,
                buildername,
            )
        else:
            # We're trying to trigger a build job and these type of jobs do
            # not require files to trigger them.
            trigger = buildername
            LOG.debug("We don't need to specify any files for %s" % buildername)

    if trigger:
        payload = {}
        # These propertie are needed for Treeherder to display running jobs
        payload['properties'] = json.dumps({
            "branch": repo_name,
            "revision": revision
        })
        payload['files'] = json.dumps(files)

        url = r'''%s/%s/builders/%s/%s''' % (
            buildapi.HOST_ROOT,
            repo_name,
            trigger,
            revision
        )

        if not dry_run:
            for _ in range(times):
                list_of_requests.append(buildapi.make_request(url, payload, AUTH))
            return list_of_requests
        else:
            # We could use HTTPPretty to mock an HTTP response
            # https://github.com/gabrielfalcao/HTTPretty
            LOG.info("We were going to post to this url: %s" % url)
            LOG.info("With this payload: %s" % str(payload))
            LOG.info("With these files: %s" % str(files))
    else:
        LOG.debug("Nothing needs to be triggered")


def trigger_range(buildername, repo_name, revisions, times, dry_run=False):
    '''
    Schedule the job named "buildername" ("times" times) from "start_revision" to
    "end_revision".
    '''
    for rev in revisions:
        LOG.debug("We want to have %s jobs of %s on revision %s" %
                  (times, buildername, rev))

        # 1) How many potentially completed jobs can we get for this buildername?
        jobs = query_jobs(repo_name, rev)
        matching_jobs = _matching_jobs(buildername, jobs)
        successful_jobs = 0
        pending_jobs = 0
        running_jobs = 0

        for job in matching_jobs:
            status = buildapi.query_job_status(job)
            if status == buildapi.PENDING:
                pending_jobs += 1
            if status == buildapi.RUNNING:
                running_jobs += 1
            if status == buildapi.SUCCESS:
                successful_jobs += 1

        potential_jobs = pending_jobs + running_jobs + successful_jobs
        LOG.debug("We found %d pending jobs, %d running jobs and %d successful_jobs." %
                  (pending_jobs, running_jobs, successful_jobs))

        if potential_jobs >= times:
            LOG.info("We have %d jobs for '%s' which is enough for the %d jobs we want." %
                     (potential_jobs, buildername, times))
        else:
            # 2) If we have less potential jobs than 'times' instances then
            #    we need to fill it in.
            LOG.debug("We have found %d jobs matching '%s' on %s. We need to trigger more." %
                      (potential_jobs, buildername, rev))
            list_of_requests = \
                trigger_job(
                    repo_name,
                    rev,
                    buildername,
                    times=times-potential_jobs,
                    dry_run=dry_run)
            if list_of_requests and any(req.status_code != 202 for req in list_of_requests):
                LOG.warning("Not all requests succeeded.")

        # TODO:
        # 3) Once we trigger a build job, we have to monitor it to make sure that it finishes;
        #    at that point we have to trigger as many test jobs as we originally intended
        #    If a build job does not finish, we have to notify the user... what should it then
        #    happen?
