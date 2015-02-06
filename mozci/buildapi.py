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

# Job status meanings from:
# http://hg.mozilla.org/build/buildbot/file/0e02f6f310b4/master/buildbot/status/builder.py#l25
SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY, CANCELLED = range(7)
# XXX ask catlee what the meaning of SKIPPED is


def make_request(url, payload, auth):
    ''' We request from buildapi to trigger a job for us.

    We return the request.
    '''
    # NOTE: A good response returns json with request_id as one of the keys
    req = requests.post(url, data=payload, auth=auth)
    assert req.status_code != 401, req.reason
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
def query_jobs_schedule(repo_name, revision, auth):
    ''' It returns a list with all jobs for that revision.

    The jobs can have various status:
        - No status key:  Job pending
        - None:           Job running
        - Integer:        Job completed

    If a status is set, we can have these various values/meanings:
        SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY, CANCELLED = range(7)

    An element with status set looks like this:
    {
        u'build_id': 61826600,
        u'status': 0,
        u'branch': u'projects/ash',
        u'buildername': u'b2g_ash_flame-kk_periodic',
        u'claimed_by_name':
            u'buildbot-master94.srv.releng.use1.mozilla.com:/builds/buildbot/build1/master',
        u'buildnumber': 1,
        u'starttime': 1422671500,
        u'requests': [{
            u'complete_at': 1422677239,
            u'complete': 1,
            u'buildername': u'b2g_ash_flame-kk_periodic',
            u'claimed_at': 1422676647,
            u'priority': 0,
            u'submittime': 1422671420,
            u'reason': u"The Nightly scheduler named 'b2g_ash periodic' triggered this build",
            u'branch': u'projects/ash',
            u'request_id': 60716696,
            u'revision': u'd7e156a7a0a6d050119885d972b048c09d267e74'
        }],
        u'endtime': 1422677239,
        u'revision': u'd7e156a7a0a6d050119885d972b048c09d267e74'
    }
    '''
    url = "%s/%s/rev/%s?format=json" % (HOST_ROOT, repo_name, revision)
    LOG.debug("About to fetch %s" % url)
    req = requests.get(url, auth=auth)
    assert req.status_code != 401, req.reason

    return req.json()


def query_jobs_url(repo_name, revision):
    ''' Returns url of where a developer can login to see the
        scheduled jobs for a revision.
    '''
    return "%s/%s/rev/%s" % (HOST_ROOT, repo_name, revision)


def query_repositories(auth):
    ''' Return dictionary with information about the various repositories.

    The data about a repository looks like this:
      "ash": {
        "repo": "https://hg.mozilla.org/projects/ash",
        "graph_branches": [
          "Ash"
        ],
        "repo_type": "hg"
      },
    '''
    url = "%s/branches?format=json" % HOST_ROOT
    LOG.debug("About to fetch %s" % url)
    req = requests.get(url, auth=auth)
    assert req.status_code != 401, req.reason
    return req.json()
