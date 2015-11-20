#! /usr/bin/env python
"""
This script is designed as a way to determine meta-data about repositories.
"""
from __future__ import absolute_import
import json
import logging
import os

from buildapi_client import BuildapiAuthError, make_query_repositories_request

from mozci.errors import AuthenticationError, MozciError
from mozci.utils.authentication import get_credentials, remove_credentials
from mozci.utils.transfer import path_to_file

LOG = logging.getLogger('mozci')
REPOSITORIES_FILE = path_to_file("repositories.txt")
REPOSITORIES = {}


#
# Functions to query
#
def query_repository(repo_name):
    """
    Return dictionary with information about a specific repository.

    Raises MozciError if the repository does not exist.
    """
    repositories = query_repositories()
    if repo_name not in repositories:
        repositories = query_repositories(clobber=True)
        if repo_name not in repositories:
            raise MozciError("That repository does not exist.")

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

    Raises an AuthenticationError if the user credentials are invalid.
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
        try:
            REPOSITORIES = make_query_repositories_request(auth=get_credentials(), dry_run=False)
        except BuildapiAuthError:
            remove_credentials()
            raise AuthenticationError("Your credentials were invalid. Please try again.")

        with open(REPOSITORIES_FILE, "wb") as fd:
            json.dump(REPOSITORIES, fd)

    return REPOSITORIES
