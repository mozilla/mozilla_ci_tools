import json
import unittest

from mock import patch, Mock

from mozci.sources import buildapi

GET_CONTENT = """
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


def mock_get(content, status):
    """
    Mock of requests.get().

    The object returned must have content and status_code properties and a json method.
    """
    response = Mock()
    response.content = content

    def mock_response_json():
        return json.loads(content)

    response.json = mock_response_json
    response.status_code = status
    return response


class TestQueryJobsSchedule(unittest.TestCase):

    @patch('requests.get', return_value=mock_get(GET_CONTENT, 200))
    @patch('mozci.sources.buildapi.valid_revision', return_value=True)
    def test_call_first_time(self, valid_revision, get):
        """query_job_schedule should return the right value after calling requests.get."""
        self.assertEquals(
            buildapi.query_jobs_schedule("try", "146071751b1e"),
            json.loads(GET_CONTENT))

        assert get.call_count == 1

    @patch('requests.get', return_value=mock_get(GET_CONTENT, 200))
    @patch('mozci.sources.buildapi.valid_revision', return_value=True)
    def test_call_second_time(self, get, valid_revision):
        """Calling the function again should return us the results directly from cache."""
        self.assertEquals(
            buildapi.query_jobs_schedule("try", "146071751b1e"),
            json.loads(GET_CONTENT))
        # query_jobs_schedule should return its value directly from
        # cache without calling get
        assert get.call_count == 0

    @patch('mozci.sources.buildapi.valid_revision', return_value=True)
    @patch('requests.get', return_value=mock_get(GET_CONTENT, 400))
    def test_bad_request(self, valid_revision, get):
        """If a bad return value is found in requests we should raise an Error."""
        with self.assertRaises(AssertionError):
            buildapi.query_jobs_schedule("try", "146071751b1e")

    @patch('mozci.sources.buildapi.valid_revision', return_value=False)
    @patch('requests.get', return_value=mock_get(GET_CONTENT, 200))
    def test_bad_revision(self, valid_revision, get):
        """If an invalid revision is passed, query_jobs_schedule should raise an Exception ."""
        with self.assertRaises(Exception):
            buildapi.query_jobs_schedule("try", "146071751b1e")
