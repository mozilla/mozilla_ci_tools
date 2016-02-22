#! /usr/bin/env python
"""
This script is designed as a way to determine meta-data about repositories.
"""
from __future__ import absolute_import
import json
import logging
import os

from thclient import TreeherderClient

from mozci.errors import MozciError
from mozci.utils.transfer import path_to_file

LOG = logging.getLogger('mozci')
REPOSITORIES_FILE = path_to_file("repositories.txt")
REPOSITORIES = {}
TREEHERDER_URL = 'treeherder.mozilla.org'


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

        th_client = TreeherderClient(protocol='https', host=TREEHERDER_URL)
        treeherderRepos = th_client.get_repositories()
        REPOSITORIES = {}
        for th_repo in treeherderRepos:
            if th_repo['active_status'] == "active":
                repo = {}
                repo['repo'] = th_repo['url']
                repo['repo_type'] = th_repo['dvcs_type']
                repo['graph_branches'] = [th_repo['name'].capitalize()]
                REPOSITORIES[th_repo['name']] = repo

        with open(REPOSITORIES_FILE, "wb") as fd:
            json.dump(REPOSITORIES, fd)

    return REPOSITORIES
