#! /usr/bin/env python
"""
This script is designed to trigger jobs through Release Engineering's
buildapi self-serve service.

The API documentation is in here (behind LDAP):
https://secure.pub.build.mozilla.org/buildapi/self-serve

The docs can be found in here:
http://moz-releng-buildapi.readthedocs.org
"""
import json
import logging

import requests
from bs4 import BeautifulSoup

from allthethings import valid_builder
from buildjson import query_buildjson_info
from platforms import associated_build_job, does_builder_need_files

LOG = logging.getLogger()

BUILDAPI = 'https://secure.pub.build.mozilla.org/buildapi/self-serve'


def _public_url(url):
    ''' If we run the script outside the Release Engineering infrastructure
        we need to use the public interface rather than the internal one.
    '''
    replace_urls = [
        ("http://pvtbuilds.pvt.build",
         "https://pvtbuilds"),
        ("http://tooltool.pvt.build.mozilla.org/build",
         "https://secure.pub.build.mozilla.org/tooltool/pvt/build")
    ]
    for from_, to_ in replace_urls:
        if url.startswith(from_):
            new_url = url.replace(from_, to_)
            LOG.debug("Replacing url %s ->\n %s" % (url, new_url))
            return new_url
    return url


def _make_request(url, payload, auth):
    # NOTE: A good response returns json with request_id as one of the keys
    req = requests.post(url, data=payload, auth=auth)
    LOG.debug("We have received this request:")
    LOG.debug(" - status code: %s" % req.status_code)
    LOG.debug(" - text:        %s" % BeautifulSoup(req.text).get_text())
    return req


def _all_urls_reachable(urls, auth=None):
    ''' Determine if the URLs are reachable
    '''
    for url in urls:
        url_tested = _public_url(url)
        LOG.debug("We are going to test if we can reach %s" % url_tested)
        requests.head(url_tested, auth=auth)


def _matching_jobs(buildername, all_jobs):
    '''
    It returns all jobs that matched the criteria.
    '''
    matching_jobs = []
    for j in all_jobs:
        if j["buildername"] == buildername:
            matching_jobs.append(j)

    return matching_jobs


def _find_files(job):
    '''
    This function helps us find the files needed to trigger a job.
    '''
    files = []

    # Let's grab the last job
    claimed_at = job["requests"][0]["claimed_at"]
    request_id = job["requests"][0]["request_id"]

    # XXX: This call takes time
    status_info = query_buildjson_info(claimed_at, request_id)
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
    build_buildername = associated_build_job(buildername, repo_name)
    # Let's figure out which jobs are associated to such revision
    all_jobs = query_jobs(repo_name, revision, auth)
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
        not_completed_job = None

        LOG.debug("List of matching jobs:")
        for job in matching_jobs:
            LOG.debug(job)
            status = job.get("status")
            if status == 0:
                # XXX: How do we determine if it
                # succeeded?
                successful_job = job
                break
            else:
                not_completed_job = job

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
        elif not_completed_job:
            LOG.debug("We are waiting for a build to finish.")
            LOG.debug(str(not_completed_job))
        else:
            LOG.debug("We are going to trigger %s instead of %s" %
                      (build_buildername, buildername))
            buildername = build_buildername

    return trigger, files


def _valid_builder(repo_name, buildername, auth):
    raise Exception("Not implemented because of bug 1087336. Use "
                    "mozci.allthethings.")


def trigger_job(repo_name, revision, buildername, auth,
                files=None, dry_run=False):
    ''' This function triggers a job through self-serve
    '''
    trigger = None

    if not valid_builder(repo_name, buildername):
        LOG.error("The builder %s requested is invalid" % buildername)
        # XXX How should we exit cleanly?
        exit(-1)

    if files:
        trigger = buildername
        _all_urls_reachable(files, auth)
    else:
        # XXX: We should not need this if clause
        if does_builder_need_files(buildername):
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
            BUILDAPI,
            repo_name,
            trigger,
            revision)
        if not dry_run:
            return _make_request(url, payload, auth)
        else:
            # We could use HTTPPretty to mock an HTTP response
            # https://github.com/gabrielfalcao/HTTPretty
            LOG.info("We were going to post to this url: %s" % url)
            LOG.info("With this payload: %s" % str(payload))
            LOG.info("With these files: %s" % str(files))
    else:
        LOG.debug("Nothing needs to be triggered")


#
# Query type of functions
#
def jobs_running_url(repo_name, revision):
    ''' Returns url of where a developer can login to see the
        scheduled jobs for this revision.
    '''
    return "%s/%s/rev/%s" % (BUILDAPI, repo_name, revision)


def query_jobs(repo_name, revision, auth):
    ''' It returns a json object with all jobs for that revision.

    Load this URL to see what to expect:
    https://secure.pub.build.mozilla.org/buildapi/self-serve/
    mozilla-central/rev/1dd013ece082?format=json
    '''
    url = "%s/%s/rev/%s?format=json" % (BUILDAPI, repo_name, revision)
    LOG.debug("About to fetch %s" % url)
    r = requests.get(url, auth=auth)
    if not r.ok:
        LOG.error(r.reason)

    return r.json()
