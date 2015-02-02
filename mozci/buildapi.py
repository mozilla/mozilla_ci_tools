#! /usr/bin/env python
"""
This script is designed to trigger jobs through Release Engineering's
buildapi self-serve service.

The API documentation is in here (behind LDAP):
https://secure.pub.build.mozilla.org/buildapi/self-serve

The docs can be found in here:
http://moz-releng-buildapi.readthedocs.org
"""
import logging

import requests
from bs4 import BeautifulSoup

LOG = logging.getLogger()

HOST_ROOT = 'https://secure.pub.build.mozilla.org/buildapi/self-serve'


def make_request(url, payload, auth):
    ''' We request from buildapi to trigger a job for us.

    We return the request.
    '''
    # NOTE: A good response returns json with request_id as one of the keys
    req = requests.post(url, data=payload, auth=auth)
    LOG.debug("We have received this request:")
    LOG.debug(" - status code: %s" % req.status_code)
    LOG.debug(" - text:        %s" % BeautifulSoup(req.text).get_text())
    return req


def _valid_builder():
    ''' Not implemented function '''
    raise Exception("Not implemented because of bug 1087336. Use "
                    "mozci.allthethings.")


#
# Functions to query
#
def jobs_running_url(repo_name, revision):
    ''' Returns url of where a developer can login to see the
        scheduled jobs for this revision.
    '''
    return "%s/%s/rev/%s" % (HOST_ROOT, repo_name, revision)


def query_jobs(repo_name, revision, auth):
    ''' It returns a json object with all jobs for that revision.

    Load this URL to see what to expect:
    https://secure.pub.build.mozilla.org/buildapi/self-serve/
    mozilla-central/rev/1dd013ece082?format=json
    '''
    url = "%s/%s/rev/%s?format=json" % (HOST_ROOT, repo_name, revision)
    LOG.debug("About to fetch %s" % url)
    req = requests.get(url, auth=auth)
    if not req.ok:
        LOG.error(req.reason)

    return req.json()
