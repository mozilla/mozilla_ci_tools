#! /usr/bin/env python
"""
This script is designed to trigger jobs through Release Engineering's
buildapi self-serve service.
"""
import json
import requests
import logging
from bs4 import BeautifulSoup

log = logging.getLogger()

BUILDAPI='https://secure.pub.build.mozilla.org/buildapi/self-serve'

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
    # XXX: A good response returns json with request_id as one of the keys
    return r

def _all_files_exist(files, auth=None):
    ''' Determine if all files are reachable
    '''
    for url in files:
        url_tested = _public_url(url)
        log.debug("We are going to test if we can reach %s" % url_tested)
        r = requests.head(url_tested, auth=auth)

def trigger(repo_name, revision, buildername, auth,
           installer_url=None, test_url=None,
           dry_run=False):
    ''' This function triggers a job through self-serve
    '''

    _all_files_exist([installer_url, test_url], auth)

    payload = {}
    # These propertie are needed for Treeherder to display running jobs
    payload['properties'] = json.dumps({
        "branch": repo_name,
        "revision": revision
    })
    payload['files'] = json.dumps(installer_url, test_url)

    url = r'''%s/%s/builders/%s/%s''' % (BUILDAPI, repo_name, buildername, revision)
    if not dry_run:
        return _make_request(url, payload, auth)
    else:
        # We could use HTTPPretty to mock an HTTP response
        # https://github.com/gabrielfalcao/HTTPretty
        log.info("We were going to post to this url: %s" % url)
        log.info("With this payload: %s" % str(payload))

# XXX: I think we should keep querying functions in this module; rework repo
# structure
def jobs_running_url(repo_name, revision):
    return "%s/%s/%s" % (BUILDAPI, repo_name, revision)
