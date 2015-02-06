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

# Self-serve cannot give us the whole granularity of states; Use buildjson where necessary.
# http://hg.mozilla.org/build/buildbot/file/0e02f6f310b4/master/buildbot/status/builder.py#l25
PENDING, RUNNING, UNKNOWN = range(-3, 0)
SUCCESS, WARNING, FAILURE, SKIPPED, EXCEPTION, RETRY, CANCELLED = range(7)


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
def query_job_schedule_info(job):
    '''
    Helper to determine the scheduling status of a job from self-serve.
    '''
    if not ("status" in job):
        return PENDING
    else:
        status = job["status"]
        if status is None:
            if "endtime" in job:
                return RUNNING
            else:
                return UNKNOWN
        elif status in (SUCCESS, WARNING, FAILURE, EXCEPTION, RETRY, CANCELLED):
            return status
        else:
            LOG.debug(job)
            raise Exception("Unexpected status")


def query_jobs_schedule(repo_name, revision, auth):
    ''' It returns a list with all jobs for that revision.
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
