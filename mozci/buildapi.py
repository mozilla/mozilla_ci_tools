#! /usr/bin/env python
"""
This script is designed to trigger jobs through Release Engineering's
buildapi self-serve service.

The API documentation is in here (behind LDAP):
https://secure.pub.build.mozilla.org/buildapi/self-serve

The docs can be generated from:
http://hg.mozilla.org/build/buildapi
"""
import json
import logging

import requests
from bs4 import BeautifulSoup

from platforms import associated_build_job
from buildjson import query_buildjson_info

log = logging.getLogger()

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
            log.debug("Replacing url %s ->\n %s" % (url, new_url))
            return new_url
    return url


def _make_request(url, payload, auth):
    r = requests.post(url, data=payload, auth=auth)
    log.debug("We have received this request:")
    log.debug(" - status code: %s" % r.status_code)
    log.debug(" - text:        %s" % BeautifulSoup(r.text).get_text())
    # NOTE: A good response returns json with request_id as one of the keys
    return r


def _all_files_exist(files, auth=None):
    ''' Determine if all files are reachable
    '''
    for url in files:
        url_tested = _public_url(url)
        log.debug("We are going to test if we can reach %s" % url_tested)
        requests.head(url_tested, auth=auth)


def trigger(repo_name, revision, buildername, auth,
            files=[], dry_run=False):
    ''' This function triggers a job through self-serve
    '''
    payload = {}
    # These propertie are needed for Treeherder to display running jobs
    payload['properties'] = json.dumps({
        "branch": repo_name,
        "revision": revision
    })

    if files:
        payload['files'] = json.dumps(files)
    elif -1 == (buildername.find("opt") or
                buildername.find("debug") or
                buildername.find("talos")):
        # XXX: The above condition is tied to buildername naming since we lack
        #      and API.
        # XXX: We could determine this by looking if the builder belongs to
        #      the right schedulers in allthethings.json
        log.debug("We don't need to specify any files for %s" % buildername)
    else:
        # For test and talos jobs we need to determine
        # what installer and test urls to use.

        # Let's figure out the associated build job
        build_buildername = associated_build_job(buildername, repo_name)

        # Let's figure through buildapi which jobs that are associated to
        # such revision
        all_jobs = query_jobs(repo_name, revision, auth)

        # Let's only look at jobs that match such build_buildername
        matching_jobs = []
        for j in all_jobs:
            if j["buildername"] == build_buildername:
                matching_jobs.append(j)

        if len(matching_jobs) == 0:
            # There is no build that triggered our test job.
            # We need to trigger the build.
            # XXX: What happens if there is already a build running?
            pass
        else:
            # Let's grab the last job
            scheduling_info = matching_jobs[-1]
            claimed_at = scheduling_info["requests"][0]["claimed_at"]
            request_id = scheduling_info["requests"][0]["request_id"]
            # XXX: This call takes time
            status_info = query_buildjson_info(claimed_at, request_id)
            properties = status_info.get("properties")
            if properties:
                if "packageUrl" in properties:
                    files.append(properties["packageUrl"])
                if "testsUrl" in properties:
                    files.append(properties["testsUrl"])

    _all_files_exist(files, auth)

    url = r'''%s/%s/builders/%s/%s''' % (BUILDAPI, repo_name, buildername,
                                         revision)
    if not dry_run:
        return _make_request(url, payload, auth)
    else:
        # We could use HTTPPretty to mock an HTTP response
        # https://github.com/gabrielfalcao/HTTPretty
        log.info("We were going to post to this url: %s" % url)
        log.info("With this payload: %s" % str(payload))
        log.info("With these files: %s" % str(files))


#
# Query type of functions
#
def jobs_running_url(repo_name, revision):
    ''' Returns url of where a developer can login to see the
        scheduled jobs for this revision.
    '''
    return "%s/%s/%s" % (BUILDAPI, repo_name, revision)


def query_jobs(repo_name, revision, auth):
    ''' It returns a json object with all jobs for that revision.

    Load this URL to see what to expect:
    https://secure.pub.build.mozilla.org/buildapi/self-serve/
    mozilla-central/rev/1dd013ece082?format=json
    '''
    url = "%s/%s/rev/%s?format=json" % (BUILDAPI, repo_name, revision)
    log.debug("About to fetch %s" % url)
    r = requests.get(url, auth=auth)
    if not r.ok:
        log.error(r.reason)

    return r.json()


def query_branches():
    # https://secure.pub.build.mozilla.org/buildapi/self-serve/branches
    raise Exception("Not implemented")
