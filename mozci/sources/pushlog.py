#! /usr/bin/env python
# coding: utf-8
'''
This helps us query information about Mozilla's Mercurial repositories.

Documentation found in here:
http://mozilla-version-control-tools.readthedocs.org/en/latest/hgmo/pushlog.html

Important notes from the pushlog documentation:

When implementing agents that consume pushlog data, please keep in mind
the following best practices:
* Query by push ID, not by changeset or date.
* Always specify a startID and endID.
* Try to avoid full if possible.
* Always use the latest format version.
* Don’t be afraid to ask for a new pushlog feature to make your life easier.
'''
import logging

import requests

LOG = logging.getLogger()
JSON_PUSHES = "%(repo_url)s/json-pushes"


def query_revisions_range(repo_url, start_revision, end_revision, version=2):
    '''
    This returns an ordered list of revisions (by date - newest first).

    repo           - represents the URL to clone a repo
    start_revision - from which revision to start with
    end_revision   - from which revision to end with
    version        - version of json-pushes to use (see docs)
    '''
    revisions = []
    url = "%s?fromchange=%s&tochange=%s&version=%s" % (
        JSON_PUSHES % {"repo_url": repo_url},
        start_revision,
        end_revision,
        version
    )
    LOG.debug("About to fetch %s" % url)
    req = requests.get(url)
    pushes = req.json()["pushes"]
    for push_id in sorted(pushes.keys()):
        # Querying by push ID is preferred because date ordering is
        # not guaranteed (due to system clock skew)
        # We can interact with self-serve with the 12 char representation
        revisions.append(pushes[push_id]["changesets"][-1][0:12])

    # json-pushes does not include the starting revision
    revisions.append(start_revision)

    return revisions


def query_pushid_range(repo_url, start_id, end_id, version=2):
    '''
    This returns an ordered list of revisions (by date - newest first).

    repo     - represents the URL to clone a repo
    start_id - from which pushid to start with
    end_id   - from which pushid to end with
    version  - version of json-pushes to use (see docs)
    '''
    revisions = []
    url = "%s?startID=%s&endID=%s&version=%s&tipsonly=1" % (
        JSON_PUSHES % {"repo_url": repo_url},
        start_id-1,  # off by one to compenstate for pushlog as it skips start_id
        end_id,
        version
    )
    LOG.debug("About to fetch %s" % url)
    req = requests.get(url)
    pushes = req.json()["pushes"]
    for push_id in sorted(pushes.keys()):
        # Querying by push ID is preferred because date ordering is
        # not guaranteed (due to system clock skew)
        # We can interact with self-serve with the 12 char representation
        revisions.append(pushes[push_id]["changesets"][-1][0:12])

    return revisions


def query_revisions_range_from_revision_and_delta(repo_url, revision, repo_name, delta):
    '''
    Function to get the start revision and end revision
    based on given delta for the given push_revision.
    '''
    try:
        push_info = query_changeset(repo_url, revision)
        pushid = int(push_info["pushid"])
        start_id = pushid - delta
        end_id = pushid + delta
        revlist = query_pushid_range(repo_url, start_id, end_id)
    except:
        raise Exception('Unable to retrieve pushlog data. '
                        'Please check repo_name and revision specified.')

    return revlist


def query_changeset(repo_url, revision):
    '''
    It returns a dictionary with meta-data about a push including:
        * changesets
        * date
        * user
    '''
    url = "%s?changeset=%s" % (JSON_PUSHES % {"repo_url": repo_url}, revision)
    LOG.debug("About to fetch %s" % url)
    req = requests.get(url)
    data = req.json()
    assert len(data) == 1, "We should only have information about one push"
    push_id, push_info = data.popitem()
    push_info["pushid"] = push_id
    LOG.debug("Push info: %s" % str(push_info))
    return push_info
