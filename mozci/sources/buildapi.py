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
import logging
import os

import requests
import ujson as json

from mozci.utils.authentication import get_credentials, remove_credentials, \
    AuthenticationError
from mozci.utils.transfer import path_to_file
from mozci.sources import pushlog

LOG = logging.getLogger('mozci')
HOST_ROOT = 'https://secure.pub.build.mozilla.org/buildapi/self-serve'
REPOSITORIES_FILE = path_to_file("repositories.txt")
REPOSITORIES = {}


class BuildapiException(Exception):
    pass


def trigger_arbitrary_job(repo_name, builder, revision, files=[], dry_run=False,
                          extra_properties=None):
    """
    Request buildapi to trigger a job for us.

    We return the request or None if dry_run is True.
    """
    url = _builders_api_url(repo_name, builder, revision)
    payload = _payload(repo_name, revision, files, extra_properties)

    if dry_run:
        LOG.info("Dry-run: We were going to request a job for '%s'" % builder)
        LOG.info("         with this payload: %s" % str(payload))
        return None

    # NOTE: A good response returns json with request_id as one of the keys
    req = requests.post(
        url,
        headers={'Accept': 'application/json'},
        data=payload,
        auth=get_credentials()
    )
    if req.status_code == 401:
        remove_credentials()
        raise AuthenticationError("Your credentials were invalid. Please try again.")

    content = req.json()
    LOG.debug("Status of the request: %s" %
              _jobs_api_url(content["request_id"]))

    return req


def make_retrigger_request(repo_name, request_id, count=1, priority=0, dry_run=True):
    """
    Retrigger a request using buildapi self-serve. Returns a request.

    Buildapi documentation:
    POST  /self-serve/{branch}/request
    Rebuild `request_id`, which must be passed in as a POST parameter.
    `priority` and `count` are also accepted as optional
    parameters. `count` defaults to 1, and represents the number
    of times this build  will be rebuilt.
    """
    url = '{}/{}/request'.format(HOST_ROOT, repo_name)
    payload = {'request_id': request_id}

    if count != 1 or priority != 0:
        payload.update({'count': count,
                        'priority': priority})

    if dry_run:
        LOG.info('We would make a POST request to %s with the payload: %s' % (url, str(payload)))
        return None

    LOG.info("We're going to re-trigger an existing completed job with request_id: %s %i time(s)."
             % (request_id, count))
    req = requests.post(
        url,
        headers={'Accept': 'application/json'},
        data=payload,
        auth=get_credentials()
    )
    # TODO: add debug message with job_id URL.
    return req


def make_cancel_request(repo_name, request_id, dry_run=True):
    """
    Cancel a request using buildapi self-serve. Returns a request.

    Buildapi documentation:
    DELETE /self-serve/{branch}/request/{request_id} Cancel the given request
    """
    url = '{}/{}/request/{}'.format(HOST_ROOT, repo_name, request_id)
    if dry_run:
        LOG.info('We would make a DELETE request to %s.' % url)
        return None

    LOG.info("We're going to cancel the job at %s" % url)
    req = requests.delete(url, auth=get_credentials())
    # TODO: add debug message with the canceled job_id URL. Find a way
    # to do that without doing an additional request.
    return req


def _builders_api_url(repo_name, builder, revision):
    return r'''%s/%s/builders/%s/%s''' % (
        HOST_ROOT,
        repo_name,
        builder,
        revision
    )


def _jobs_api_url(job_id):
    """This is the URL to a self-serve job request (scheduling, canceling, etc)."""
    return r'''%s/jobs/%s''' % (HOST_ROOT, job_id)


def _payload(repo_name, revision, files=[], extra_properties=None):

    # These properties are needed for Treeherder to display running jobs.
    # Additional properties may be specified by a user.
    props = {
        "branch": repo_name,
        "revision": revision,
    }
    props.update(extra_properties or {})

    payload = {
        'properties': json.dumps(props, sort_keys=True)
    }

    if files:
        payload['files'] = json.dumps(files)

    return payload


def _valid_builder():
    """Not implemented function."""
    raise Exception("Not implemented because of bug 1087336. Use "
                    "mozci.allthethings.")


def valid_credentials():
    """Verify that the user's credentials are valid."""
    LOG.debug("Determine if the user's credentials are valid.")
    req = requests.get(HOST_ROOT, auth=get_credentials())
    if req.status_code == 401:
        remove_credentials()
        raise AuthenticationError("Your credentials were invalid. Please try again.")


#
# Functions to query
#
def query_jobs_schedule(repo_name, revision):
    """ Query Buildapi for jobs """
    repo_url = query_repo_url(repo_name)
    if not pushlog.valid_revision(repo_url, revision):
        raise BuildapiException

    url = "%s/%s/rev/%s?format=json" % (HOST_ROOT, repo_name, revision)
    LOG.debug("About to fetch %s" % url)
    req = requests.get(url, auth=get_credentials())

    # If the revision doesn't exist on buildapi, that means there are
    # no builapi jobs for this revision
    if req.status_code not in [200]:
        return []

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
        if req.status_code == 401:
            remove_credentials()
            raise AuthenticationError("Your credentials were invalid. Please try again.")

        REPOSITORIES = req.json()
        with open(REPOSITORIES_FILE, "wb") as fd:
            json.dump(REPOSITORIES, fd)

    return REPOSITORIES
