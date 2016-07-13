#! /usr/bin/env python
"""
This script is designed as a way to determine meta-data about repositories.
"""
from __future__ import absolute_import
import logging

from thclient import TreeherderClient

from mozci.errors import MozciError

LOG = logging.getLogger('mozci')
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
        repositories = query_repositories(clear_cache=True)
        if repo_name not in repositories:
            raise MozciError("That repository does not exist.")

    return repositories[repo_name]


def query_repo_url(repo_name):
    LOG.debug("Determine repository associated to %s" % repo_name)
    return query_repository(repo_name)["repo"]


def query_repositories(clear_cache=False):
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
    LOG.debug("Query repositories")
    global REPOSITORIES

    if clear_cache:
        REPOSITORIES = {}

    if REPOSITORIES:
        return REPOSITORIES

    th_client = TreeherderClient()
    treeherderRepos = th_client.get_repositories()
    REPOSITORIES = {}
    for th_repo in treeherderRepos:
        if th_repo['active_status'] == "active":
            REPOSITORIES[th_repo['name']] = {
                'repo': th_repo['url'],
                'repo_type': th_repo['dvcs_type'],
                'graph_branches': [th_repo['name'].capitalize()],
            }

    return REPOSITORIES
