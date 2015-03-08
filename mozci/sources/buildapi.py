#! /usr/bin/env python
"""
This script is designed to trigger jobs through Release Engineering's
buildapi self-serve service.

The API documentation is in here (behind LDAP):
https://secure.pub.build.mozilla.org/buildapi/self-serve

The docs can be found in here:
http://moz-releng-buildapi.readthedocs.org
"""
from __future__ import absolute_import
import json
import logging
import os

import requests
from bs4 import BeautifulSoup

from mozci.utils.authentication import get_credentials
from mozci.sources.pushlog import query_revision_info
from mozci.sources.buildjson import query_job_data

LOG = logging.getLogger()
HOST_ROOT = 'https://secure.pub.build.mozilla.org/buildapi/self-serve'
REPOSITORIES_FILE = os.path.abspath("repositories.txt")
REPOSITORIES = {}

# Self-serve cannot give us the whole granularity of states; Use buildjson where necessary.
# http://hg.mozilla.org/build/buildbot/file/0e02f6f310b4/master/buildbot/status/builder.py#l25
PENDING, RUNNING, COALESCED, UNKNOWN = range(-4, 0)
SUCCESS, WARNING, FAILURE, SKIPPED, EXCEPTION, RETRY, CANCELLED = range(7)
RESULTS = ["success", "warnings", "failure", "skipped", "exception", "retry",
           "cancelled", "pending", "running", "coalesced", "unknown"]


class BuildapiException(Exception):
    pass


def make_request(repo_name, builder, revision, files=[], dry_run=False):
    """
    Request buildapi to trigger a job for us.

    We return the request or None if dry_run is True.
    """
    url = _api_url(repo_name, builder, revision)
    payload = _payload(repo_name, revision, files)

    if dry_run:
        LOG.info("Dry-run: We were going to post to this url: %s" % url)
        LOG.info("Dry-run: with this payload: %s" % str(payload))
        return None

    # NOTE: A good response returns json with request_id as one of the keys
    req = requests.post(url, data=payload, auth=get_credentials())
    assert req.status_code != 401, req.reason
    LOG.debug("We have received this request:")
    LOG.debug(" - status code: %s" % req.status_code)
    LOG.debug(" - text:        %s" % BeautifulSoup(req.text).get_text())
    return req


def _api_url(repo_name, builder, revision):
    return r'''%s/%s/builders/%s/%s''' % (
        HOST_ROOT,
        repo_name,
        builder,
        revision
    )


def _payload(repo_name, revision, files=[]):
    payload = {}
    # These properties are needed for Treeherder to display running jobs
    payload['properties'] = json.dumps({
        "branch": repo_name,
        "revision": revision
    })

    if files:
        payload['files'] = json.dumps(files)

    return payload


def _valid_builder():
    """Not implemented function."""
    raise Exception("Not implemented because of bug 1087336. Use "
                    "mozci.allthethings.")


def valid_revision(repo_name, revision):
    """
    There are revisions that won't exist in buildapi.

    For instance, commits with DONTBUILD will not exist.
    """
    LOG.debug("Determine if the revision is valid for buildapi.")
    revision_info = query_revision_info(query_repo_url(repo_name), revision, full=True)
    if "DONTBUILD" in revision_info["changesets"][-1]["desc"]:
        LOG.info("We will _NOT_ trigger anything for revision %s for %s since "
                 "it does not exist in self-serve." % (revision, repo_name))
        return False
    else:
        return True


#
# Functions to query
#
def query_job_status(job):
    """Helper to determine the scheduling status of a job from self-serve."""
    if not ("status" in job):
        return PENDING
    else:
        status = job["status"]
        if status is None:
            if "endtime" in job:
                return RUNNING
            else:
                return UNKNOWN
        elif status == SUCCESS:
            # The success status for self-serve can actually be a coalesced job
            req = job["requests"][0]
            status_data = query_job_data(
                req["complete_at"],
                req["request_id"])
            if status_data["properties"]["revision"][0:12] != req["revision"][0:12]:
                return COALESCED
            else:
                return SUCCESS

        elif status in (WARNING, FAILURE, EXCEPTION, RETRY, CANCELLED):
            return status
        else:
            LOG.debug(job)
            raise Exception("Unexpected status")


def query_jobs_schedule(repo_name, revision):
    """
    Return a list with all jobs for that revision.

    If we can't query about this revision in buildapi we return an empty list.

    raises BuildapiException
    """
    if not valid_revision(repo_name, revision):
        raise BuildapiException

    url = "%s/%s/rev/%s?format=json" % (HOST_ROOT, repo_name, revision)
    LOG.debug("About to fetch %s" % url)
    req = requests.get(url, auth=get_credentials())
    assert req.status_code in [200], req.content

    return req.json()


def query_jobs_url(repo_name, revision):
    """Return URL of where a developer can login to see the scheduled jobs for a revision."""
    return "%s/%s/rev/%s" % (HOST_ROOT, repo_name, revision)


def query_repository(repo_name):
    """Return dictionary with information about a specific repository."""
    repositories = query_repositories()
    if repo_name not in repositories:
        repositories = query_repositories(clobber=True)
        if repo_name not in repositories:
            raise Exception("That repository does not exist.")

    return repositories[repo_name]


def query_repo_url(repo_name):
    LOG.debug("Determine repository associated to %s" % repo_name)
    return query_repository(repo_name)["repo"]


def query_repositories(clobber=False):
    """
    Return dictionary with information about the various repositories.

    The data about a repository looks like this:

    .. code-block:: python

        "ash": {
            "repo": "https://hg.mozilla.org/projects/ash",
            "graph_branches": ["Ash"],
            "repo_type": "hg"
        }
    """
    global REPOSITORIES

    if clobber:
        REPOSITORIES = {}
        if os.path.exists(REPOSITORIES_FILE):
            os.remove(REPOSITORIES_FILE)

    if REPOSITORIES:
        return REPOSITORIES

    if os.path.exists(REPOSITORIES_FILE):
        LOG.debug("Loading %s" % REPOSITORIES_FILE)
        fd = open(REPOSITORIES_FILE)
        REPOSITORIES = json.load(fd)
    else:
        url = "%s/branches?format=json" % HOST_ROOT
        LOG.debug("About to fetch %s" % url)
        req = requests.get(url, auth=get_credentials())
        assert req.status_code != 401, req.reason
        REPOSITORIES = req.json()
        with open(REPOSITORIES_FILE, "wb") as fd:
            json.dump(REPOSITORIES, fd)

    return REPOSITORIES
