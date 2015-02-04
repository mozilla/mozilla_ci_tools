#! /usr/bin/env python
# coding: utf-8
'''
This helps us query information about Mozilla's Mercurial repositories.

Documentation found in here:
http://mozilla-version-control-tools.readthedocs.org/en/latest/hgmo/pushlog.html

Important notes from the documentation:
---------------------------------------
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
JSON_PUSHES = "%(repo_path)s/json-pushes"


def query_revisions_range(repo, start_revision, end_revision, version=2):
    '''
    This returns an ordered list of revisions (by date - newest first).

    repo           - represents the URL to clone a repo
    start_revision - from which revision to start with
    end_revision   - from which revision to end with
    version        - version of json-pushes to use (see docs)
    '''
    revisions = []
    url = "%s?fromchange=%s&tochange=%s&version=%s" % (
        JSON_PUSHES % {"repo_path": repo},
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
        # We can interact with self-server with the 12 char representation
        revisions.append(pushes[push_id]["changesets"][-1][0:12])

    if revisions:
        # json-pushes does not include the starting revision
        revisions.append(start_revision)

    return revisions
