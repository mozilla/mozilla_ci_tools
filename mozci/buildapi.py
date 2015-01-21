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

from platforms import PREFIX, JOB_TYPE

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


def _associated_build_job(buildername, repo_name):
    '''
    The prefix and the post fix of a builder name can tell us
    the type of build job that triggered it.
    e.g. Windows 8 64-bit cedar opt test mochitest-1
    e.g. b2g_ubuntu64_vm cedar opt test gaia-unit

    We would prefer to have a non-mapping approach, however,
    we have not figured out an approach to determine the graph
    of dependencies.
    '''
    prefix, job_type = buildername.split(" %s " % repo_name)
    job_type = job_type.split(" ")[0]
    return "%s %s %s" % (PREFIX[prefix], repo_name, JOB_TYPE[job_type])


def trigger(repo_name, revision, buildername, auth,
            files=[], dry_run=False):
    ''' This function triggers a job through self-serve
    '''
    _all_files_exist(files, auth)

    payload = {}
    # These propertie are needed for Treeherder to display running jobs
    payload['properties'] = json.dumps({
        "branch": repo_name,
        "revision": revision
    })

    if files:
        payload['files'] = json.dumps(files)
    elif True:  # XXX: Determine if it is a test or talos job
        # For test and talos job we need to determine
        # what installer and test urls to use.

        # Let's figure out the associated build job
        # build_buildername = _associated_build_job(buildername, repo_name)

        # Let's figure out the jobs that are associated to such revision
        # TODO

        # Let's only look at jobs that match such build_buildername
        # TODO

        # If such build job is running we don't have to trigger the test job
        # If such build job is running we don't have to trigger the test job
        '''
        info = buildjson.query_buildjson_info(59121254)
        properties = info.get("properties")
        if properties:
            if "packageUrl" in properties:
                files.append(properties["packageUrl"])
            if "testsUrl" in properties:
                files.append(properties["testsUrl"])
        '''
        files = [
            u'http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/'
            'cedar-win64/1421186363/firefox-38.0a1.en-US.win64-x86_64.zip',
            u'http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/'
            'cedar-win64/1421186363/firefox-38.0a1.en-US.win64-x86_64.tests.zip'
        ]

    url = r'''%s/%s/builders/%s/%s''' % (BUILDAPI, repo_name, buildername,
                                         revision)
    if not dry_run:
        return _make_request(url, payload, auth)
    else:
        # We could use HTTPPretty to mock an HTTP response
        # https://github.com/gabrielfalcao/HTTPretty
        log.info("We were going to post to this url: %s" % url)
        log.info("With this payload: %s" % str(payload))
        log.info("With this files: %s" % str(files))


#
# Query type of functions
#
def jobs_running_url(repo_name, revision):
    return "%s/%s/%s" % (BUILDAPI, repo_name, revision)


def query_jobs(repo_name, revision):
    ''' It returns a json object with all jobs for that revision.

        Load something like this to see it:
        %s/cedar/rev/f5947d58ab02?format=json % BUILDAPI
    '''
    raise Exception("Not implemented")


def query_branches():
    # https://secure.pub.build.mozilla.org/buildapi/self-serve/branches
    raise Exception("Not implemented")
