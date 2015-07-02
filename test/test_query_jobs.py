import json
import unittest

from mock import patch, Mock

from mozci.query_jobs import BuildApi, SUCCESS, PENDING,\
    RUNNING, UNKNOWN, COALESCED, FAILURE

BASE_JSON = """
[{
    "build_id": 72398103,
    "status": %s,
    "branch": "try",
    "buildername": "Linux x86-64 try build",
    "claimed_by_name": "buildbot-master75.bb.releng.use1.mozilla.com:/builds/buildbot/try1/master",
    "buildnumber": 4372,
    "starttime": 1433164406,
    "requests": [
        {"complete_at": %s,
         "complete": %s,
         "buildername": "Linux x86-64 try build",
         "claimed_at": 1433166028,
         "priority": 0,
         "submittime": 1433164090,
         "reason": "scheduler",
         "branch": "try",
         "request_id": 71123549,
         "revision": "146071751b1e5d16b87786f6e60485222c28c202"}],
    "endtime": %s,
    "revision": "146071751b1e5d16b87786f6e60485222c28c202"}]
"""

JOBS_SCHEDULE = BASE_JSON % (SUCCESS, 1433166610, 1, 1433166609)

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

POST_RESPONSE = """{
    "body": {
        "msg": "Ok",
        "errors": false},
    "request_id": 1234567
    }
"""

BAD_REVISION = """{
    "msg": "Revision 123456123456 not found on branch try",
    "status": "FAILED"
    }
"""


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


class TestBuildApiGetAllJobs(unittest.TestCase):

    def setUp(self):
        self.query_api = BuildApi()

    @patch('requests.get', return_value=mock_response(JOBS_SCHEDULE, 200))
    @patch('mozci.sources.buildapi.valid_revision', return_value=True)
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    def test_call_first_time(self, get_credentials, valid_revision, get):
        """_get_all_jobs should return the right value after calling requests.get."""
        self.assertEquals(
            self.query_api.get_all_jobs("try", "146071751b1e"),
            json.loads(JOBS_SCHEDULE))

        assert get.call_count == 1

    @patch('requests.get', return_value=mock_response(JOBS_SCHEDULE, 200))
    @patch('mozci.sources.buildapi.valid_revision', return_value=True)
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    def test_call_second_time(self, get_credentials, valid_revision, get):
        """Calling the function again should return us the results directly from cache."""
        self.assertEquals(
            self.query_api.get_all_jobs("try", "146071751b1e"),
            json.loads(JOBS_SCHEDULE))
        # get_all_jobs should return its value directly from
        # cache without calling get
        assert get.call_count == 0

    @patch('requests.get', return_value=mock_response(JOBS_SCHEDULE, 400))
    @patch('mozci.sources.buildapi.valid_revision', return_value=True)
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    def test_bad_request(self, get_credentials, valid_revision, get):
        """If a bad return value is found in requests we should raise an Error."""
        with self.assertRaises(AssertionError):
            self.query_api.get_all_jobs("try", "146071751b1e")

    @patch('mozci.sources.buildapi.valid_revision', return_value=False)
    def test_bad_revision(self, valid_revision):
        """If an invalid revision is passed, _get_all_jobs should raise an Exception ."""
        with self.assertRaises(Exception):
            self.query_api.get_all_jobs("try", "146071751b1e")


class TestBuildApiGetJobStatus(unittest.TestCase):
    """Test query_job_status with different types of jobs."""

    def setUp(self):
        self.query_api = BuildApi()

    def test_pending_job(self):
        """Test get_job_status with a pending job."""
        pending_job = json.loads(BASE_JSON % ('null', 'null', 0, 1433166609))[0]
        pending_job.pop("status")
        self.assertEquals(self.query_api.get_job_status(pending_job), PENDING)

    def test_running_job(self):
        """Test get_job_status with a running job."""
        running_job = json.loads(BASE_JSON % ('null', 'null', 0, 'null'))[0]
        self.assertEquals(self.query_api.get_job_status(running_job), RUNNING)

    def test_unknown_job(self):
        """Test get_job_status with an unknown job."""
        unknown_job = json.loads(BASE_JSON % ('null', 'null', 0, 1433166609))[0]
        self.assertEquals(self.query_api.get_job_status(unknown_job), UNKNOWN)

    @patch('mozci.query_jobs.BuildApi._is_coalesced', return_value=False)
    def test_successful_job(self, _is_coalesced):
        """Test get_job_status with a successful job. We will mock _is_coalesced for that."""
        successful_job = json.loads(BASE_JSON % (SUCCESS, 1433166610, 1, 1433166609))[0]
        self.assertEquals(self.query_api.get_job_status(successful_job), SUCCESS)

    @patch('mozci.query_jobs.BuildApi._is_coalesced', return_value=True)
    def test_coalesced_job(self, _is_coalesced):
        """Test get_job_status with a coalesced job. We will mock _is_coalesced for that."""
        coalesced_job = json.loads(BASE_JSON % (SUCCESS, 1433166610, 1, 1433166609))[0]
        self.assertEquals(self.query_api.get_job_status(coalesced_job), COALESCED)

    def test_failed_job(self):
        """Test get_job_status with a failed job."""
        failed_job = json.loads(BASE_JSON % (FAILURE, 1433166610, 1, 1433166609))[0]
        self.assertEquals(self.query_api.get_job_status(failed_job), FAILURE)

    def test_weird_job(self):
        """get_job_status should raise an Exception when it encounters an unexpected status."""
        weird_job = json.loads(BASE_JSON % (20, 1433166610, 1, 1433166609))[0]
        with self.assertRaises(Exception):
            self.query_api.get_job_status(weird_job)


class TestBuildApiGetMatchingJobs(unittest.TestCase):

    def setUp(self):
        self.alljobs = [
            {'build_id': 64090958,
             'status': 2,
             'branch': 'repo',
             'buildername': 'Platform repo test',
             'claimed_by_name': 'buildbot-releng-path',
             'buildnumber': 16,
             'starttime': 1424960497,
             'requests': [
                 {'complete_at': 1424961882,
                  'complete': 1,
                  'buildername': 'Platform repo test',
                  'claimed_at': 1424961710,
                  'priority': 0,
                  'submittime': 1424960493,
                  'reason': 'Self-serve: Requested by nobody@mozilla.com',
                  'branch': 'repo',
                  'request_id': 62949190,
                  'revision': '4f2decfeb9c5'}],
             'endtime': 1424961882,
             'revision': '4f2decfeb9c5'},
            {'build_id': 63420134,
             'status': 0,
             'branch': 'repo',
             'buildername': 'Platform repo other test',
             'claimed_by_name': 'buildbot-releng-path2',
             'buildnumber': 40,
             'starttime': 1424317413,
             'requests': [
                 {'complete_at': 1424319198,
                  'complete': 1,
                  'buildername': 'Platform repo other test',
                  'claimed_at': 1424318934,
                  'priority': 0,
                  'submittime': 1424314389,
                  'reason': 'scheduler',
                  'branch': 'repo',
                  'request_id': 62279073,
                  'revision': '4f2decfeb9c552c6323525385ccad4b450237e20'}],
             'endtime': 1424319198,
             'revision': u'4f2decfeb9c552c6323525385ccad4b450237e20'}]

        self.jobs = self.alljobs[:1]
        self.query_api = BuildApi()

    def test_matching_jobs_existing(self):
        """get_matching_jobs should return the whole dictionary for a buildername in alljobs."""
        assert self.query_api.get_matching_jobs('Platform repo test', self.alljobs) == self.jobs

    def test_matching_jobs_invalid(self):
        """get_matching_jobs should return an empty list if it receives an invalid buildername."""
        assert self.query_api.get_matching_jobs('Invalid buildername', self.alljobs) == []
