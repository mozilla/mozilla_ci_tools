import json
import os
import unittest

from mock import patch, Mock

from mozci import repositories

REPOSITORIES = """{
    "repo1": {
        "repo": "https://hg.mozilla.org/releases/repo1",
        "graph_branches": ["Repo1"],
        "repo_type": "hg"},
    "repo2": {
        "repo": "https://hg.mozilla.org/projects/repo2",
        "graph_branches": ["Repo2"],
        "repo_type": "hg"}
    }
"""
TH_REPOSITORIES = [{"id": 1,
                    "repository_group": {"name": "development", "description": ""},
                    "name": "repo1",
                    "dvcs_type": "hg",
                    "url": "https://hg.mozilla.org/releases/repo1",
                    "codebase": "gecko",
                    "description": "",
                    "active_status": "active"
                    },
                   {"id": 2,
                    "repository_group": {"name": "development", "description": ""},
                    "name": "repo2",
                    "dvcs_type": "hg",
                    "url": "https://hg.mozilla.org/projects/repo2",
                    "codebase": "gecko",
                    "description": "",
                    "active_status": "active"
                    },
                   {"id": 3,
                    "repository_group": {"name": "development", "description": ""},
                    "name": "repo3",
                    "dvcs_type": "hg",
                    "url": "https://hg.mozilla.org/releases/repo3",
                    "codebase": "gecko",
                    "description": "",
                    "active_status": "inactive"}]


def mock_response(content, status):
    """
    Mock of requests.get().

    The object returned must have content, status_code and reason
    properties and a json method.
    """
    response = Mock()
    response.content = content

    def mock_response_json():
        return json.loads(content)

    response.json = mock_response_json
    response.status_code = status
    response.reason = 'OK'
    return response


class TestQueryRepositories(unittest.TestCase):

    def setUp(self):
        repositories.REPOSITORIES_FILE = 'tmp_repositories.txt'

    def tearDown(self):
        if os.path.exists('tmp_repositories.txt'):
            os.remove('tmp_repositories.txt')

    @patch('thclient.TreeherderClient.get_repositories', return_value=TH_REPOSITORIES)
    def test_call_without_any_cache(self, get_repositories):
        """Calling the function without disk or in-memory cache."""
        self.assertEquals(
            repositories.query_repositories(), json.loads(REPOSITORIES))

        self.assertEquals(
            repositories.REPOSITORIES, json.loads(REPOSITORIES))

    def test_in_memory_cache(self):
        """Calling the function without disk cache but with in-memory cache."""
        repositories.REPOSITORIES = json.loads(REPOSITORIES)
        self.assertEquals(
            repositories.query_repositories(), json.loads(REPOSITORIES))

    def test_file_cache(self):
        """Calling the function without in-memory caching but with file cache."""
        repositories.REPOSITORIES = {}

        # Using a different 'repositories' mock to make sure
        # query_repositories is using the right one.
        different_repositories = {"real-repo": "repo"}
        with open('tmp_repositories.txt', 'w') as f:
            json.dump(different_repositories, f)

        self.assertEquals(
            repositories.query_repositories(), different_repositories)

    @patch('thclient.TreeherderClient.get_repositories', return_value=TH_REPOSITORIES)
    def test_with_clobber(self, get_repositories):
        """When clobber is True query_repositories should ignore both caches."""
        # Using a different 'repositories' mock to make sure
        # query_repositories is using the right one.
        different_repositories = {"real-repo": "repo"}
        repositories.REPOSITORIES = different_repositories
        with open('tmp_repositories.txt', 'w') as f:
            json.dump(different_repositories, f)

        self.assertEquals(
            repositories.query_repositories(clobber=True), json.loads(REPOSITORIES))


class TestQueryRepoUrl(unittest.TestCase):

    @patch('mozci.repositories.query_repository',
           return_value=json.loads(REPOSITORIES)['repo1'])
    def test_query_repo_url_valid(self, query_repository):
        """Test query_repo_url with a mock value for query_repository."""
        self.assertEquals(
            repositories.query_repo_url('repo1'), "https://hg.mozilla.org/releases/repo1")

    @patch('mozci.repositories.query_repository',
           return_value=json.loads(REPOSITORIES))
    def test_query_repo_url_invalid(self, query_repository):
        """query_repo_url should raise an Exception when a repository not in the JSON file."""
        with self.assertRaises(Exception):
            repositories.query_repo_url("not-a-repo")


class TestQueryRepository(unittest.TestCase):

    """Test query_repository with a mock value for query_repositories."""

    @patch('mozci.repositories.query_repositories',
           return_value=json.loads(REPOSITORIES))
    def test_query_repository(self, query_repositories):
        """Test with a valid repo name."""
        self.assertEquals(
            repositories.query_repository('repo1'), json.loads(REPOSITORIES)['repo1'])

    @patch('mozci.repositories.query_repositories',
           return_value=json.loads(REPOSITORIES))
    def test_invalid(self, query_repositories):
        """query_repository should raise an Exception when the repo is invalid."""
        with self.assertRaises(Exception):
            repositories.query_repository("not-a-repo")
