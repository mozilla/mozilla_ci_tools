""" This module is generally your first starting point.
Instead of going directly to the module that represent different data sources
(e.g. buildapi.py), we highly encourage you to interface to them through here.
As the continuous integration changes, you will be better off letting mozci.py
determine which source to reach to take the actions you need.

In here, you will also find high level functions that will do various low level
interactions with distinct modules to meet your needs."""
import json
import logging

import allthethings
import buildapi
import buildjson
import platforms
import pushlog

from utils.misc import _all_urls_reachable

LOG = logging.getLogger()


def _matching_jobs(buildername, all_jobs):
    '''
    It returns all jobs that matched the criteria.
    '''
    matching_jobs = []
    for j in all_jobs:
        if j["buildername"] == buildername:
            matching_jobs.append(j)

    return matching_jobs


def _determine_trigger_objective(repo_name, revision, buildername, auth):
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
    raise Exception()
    # Let's figure out which jobs are associated to such revision
    all_jobs = buildapi.query_jobs(repo_name, revision, auth)
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
            if not _all_urls_reachable(files, auth):
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


def _find_files(job):
    '''
    This function helps us find the files needed to trigger a job.
    '''
    files = []

    # Let's grab the last job
    claimed_at = job["requests"][0]["claimed_at"]
    request_id = job["requests"][0]["request_id"]

    # XXX: This call takes time
    status_info = buildjson.query_buildjson_info(claimed_at, request_id)
    assert status_info is not None, \
        "We should not have received an empty status"

    LOG.debug("We want to find the files needed to trigger %s" %
              status_info["buildername"])

    properties = status_info.get("properties")
    if properties:
        if "packageUrl" in properties:
            files.append(properties["packageUrl"])
        if "testsUrl" in properties:
            files.append(properties["testsUrl"])

    return files


#
# Query functionality
#
def jobs_running_url(*args, **kwargs):
    ''' Return buildapi url showing running jobs.'''
    # XXX: How can I use in here the __doc__ of buildapi.jobs_running_url?
    return buildapi.jobs_running_url(*args, **kwargs)


def query_builders():
    ''' Returns list of all builders.
    '''
    return allthethings.list_builders()


def query_repositories(auth):
    ''' Returns all information about the repositories we have.
    '''
    return buildapi.query_repositories(auth)


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
def trigger_job(repo_name, revision, buildername, auth,
                files=None, dry_run=False):
    ''' This function triggers a job through self-serve
    '''
    trigger = None

    if not valid_builder(buildername):
        LOG.error("The builder %s requested is invalid" % buildername)
        # XXX How should we exit cleanly?
        exit(-1)

    if files:
        trigger = buildername
        _all_urls_reachable(files, auth)
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
                auth
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
            return buildapi.make_request(url, payload, auth)
        else:
            # We could use HTTPPretty to mock an HTTP response
            # https://github.com/gabrielfalcao/HTTPretty
            LOG.info("We were going to post to this url: %s" % url)
            LOG.info("With this payload: %s" % str(payload))
            LOG.info("With these files: %s" % str(files))
    else:
        LOG.debug("Nothing needs to be triggered")


def trigger_range(buildername, repo_name, start_revision, end_revision, times, auth, dry_run):
    '''
    Schedule the job named "buildername" ("times" times) from "start_revision" to
    "end_revision".
    '''
    repo = buildapi.query_repositories(auth)[repo_name]["repo"]
    revisions = pushlog.query_revisions_range(repo, start_revision, end_revision)
    print revisions
