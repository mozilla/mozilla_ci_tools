import json
import os
import unittest

from mock import patch, Mock

from mozci.sources import buildapi

JOBS_SCHEDULE = """
[{
    "build_id": 72398103,
    "status": 0,
    "branch": "try",
    "buildername": "Linux x86-64 try build",
    "claimed_by_name": "buildbot-master75.bb.releng.use1.mozilla.com:/builds/buildbot/try1/master",
    "buildnumber": 4372,
    "starttime": 1433164406,
    "requests": [
        {"complete_at": 1433166610,
         "complete": 1,
         "buildername": "Linux x86-64 try build",
         "claimed_at": 1433166028,
         "priority": 0,
         "submittime": 1433164090,
         "reason": "scheduler",
         "branch": "try",
         "request_id": 71123549,
         "revision": "146071751b1e5d16b87786f6e60485222c28c202"}],
    "endtime": 1433166609,
    "revision": "146071751b1e5d16b87786f6e60485222c28c202"}]
"""

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


def mock_get(content, status):
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


class TestQueryJobsSchedule(unittest.TestCase):

    @patch('requests.get', return_value=mock_get(JOBS_SCHEDULE, 200))
    @patch('mozci.sources.buildapi.valid_revision', return_value=True)
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    def test_call_first_time(self, get_credentials, valid_revision, get):
        """query_job_schedule should return the right value after calling requests.get."""
        self.assertEquals(
            buildapi.query_jobs_schedule("try", "146071751b1e"),
            json.loads(JOBS_SCHEDULE))

        assert get.call_count == 1

    @patch('requests.get', return_value=mock_get(JOBS_SCHEDULE, 200))
    @patch('mozci.sources.buildapi.valid_revision', return_value=True)
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    def test_call_second_time(self, get_credentials, valid_revision, get):
        """Calling the function again should return us the results directly from cache."""
        self.assertEquals(
            buildapi.query_jobs_schedule("try", "146071751b1e"),
            json.loads(JOBS_SCHEDULE))
        # query_jobs_schedule should return its value directly from
        # cache without calling get
        assert get.call_count == 0

    @patch('requests.get', return_value=mock_get(JOBS_SCHEDULE, 400))
    @patch('mozci.sources.buildapi.valid_revision', return_value=True)
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    def test_bad_request(self, get_credentials, valid_revision, get):
        """If a bad return value is found in requests we should raise an Error."""
        with self.assertRaises(AssertionError):
            buildapi.query_jobs_schedule("try", "146071751b1e")

    @patch('mozci.sources.buildapi.valid_revision', return_value=False)
    def test_bad_revision(self, valid_revision):
        """If an invalid revision is passed, query_jobs_schedule should raise an Exception ."""
        with self.assertRaises(Exception):
            buildapi.query_jobs_schedule("try", "146071751b1e")


class TestQueryRepositories(unittest.TestCase):

    def setUp(self):
        buildapi.REPOSITORIES_FILE = 'tmp_repositories.txt'

    def tearDown(self):
        if os.path.exists('tmp_repositories.txt'):
            os.remove('tmp_repositories.txt')

    @patch('requests.get', return_value=mock_get(REPOSITORIES, 200))
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    def test_call_without_any_cache(self, get_credentials, get):
        """Calling the function without disk or in-memory cache."""
        self.assertEquals(
            buildapi.query_repositories(), json.loads(REPOSITORIES))

        self.assertEquals(
            buildapi.REPOSITORIES, json.loads(REPOSITORIES))

    def test_in_memory_cache(self):
        """Calling the function without disk cache but with in-memory cache."""
        buildapi.REPOSITORIES = json.loads(REPOSITORIES)
        self.assertEquals(
            buildapi.query_repositories(), json.loads(REPOSITORIES))

    def test_file_cache(self):
        """Calling the function without in-memory caching but with file cache."""
        buildapi.REPOSITORIES = {}

        # Using a different 'repositories' mock to make sure
        # query_repositories is using the right one.
        different_repositories = {"real-repo": "repo"}
        with open('tmp_repositories.txt', 'w') as f:
            json.dump(different_repositories, f)

        self.assertEquals(
            buildapi.query_repositories(), different_repositories)

    @patch('requests.get', return_value=mock_get(REPOSITORIES, 200))
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    def test_with_clobber(self, get_credentials, get):
        """When clobber is True query_repositories should ignore both caches."""
        # Using a different 'repositories' mock to make sure
        # query_repositories is using the right one.
        different_repositories = {"real-repo": "repo"}
        buildapi.REPOSITORIES = different_repositories
        with open('tmp_repositories.txt', 'w') as f:
            json.dump(different_repositories, f)

        self.assertEquals(
            buildapi.query_repositories(clobber=True), json.loads(REPOSITORIES))
