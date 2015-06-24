"""This module interacts with Treeherder API."""

import requests

TREEHERDER_API_URL = "https://treeherder.mozilla.org/api"


def get_repo_tip(repo_name):
    """Find on Treeherder what revision is the repository tip."""
    url = "{}/project/{}/resultset/?count=1".format(TREEHERDER_API_URL, repo_name)
    newest_job = requests.get(url).json()
    return newest_job["results"][0]["revision"]
