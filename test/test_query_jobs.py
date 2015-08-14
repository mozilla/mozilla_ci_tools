import json
import unittest

from mock import patch, Mock

from mozci import query_jobs
from mozci.query_jobs import BuildApi, TreeherderApi, SUCCESS, PENDING,\
    RUNNING, UNKNOWN, COALESCED, FAILURE, TreeherderException
from mozci.sources import buildapi

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

TREEHERDER_JOB = """
{
    "submit_timestamp": 1435806434,
    "build_system_type": "buildbot",
    "machine_name": "tst-linux64-spot-1083",
    "job_group_symbol": "M",
    "job_group_name": "Mochitest",
    "platform_option": "opt",
    "job_type_description": "integration test",
    "result_set_id": 16679,
    "build_platform_id": 9,
    "result": "%s",
    "id": 11294317,
    "machine_platform_architecture": "x86_64",
    "end_timestamp": 1435807607,
    "build_platform": "linux64",
    "job_guid": "56e77044a516ff857a21ebd52a97d73f7fdf29de",
    "job_type_name": "Mochitest",
    "ref_data_name": "Ubuntu VM 12.04 x64 mozilla-inbound opt test mochitest-1",
    "platform": "linux64",
    "state": "%s",
    "running_eta": 1907,
    "pending_eta": 6,
    "build_os": "linux",
    "option_collection_hash": "102210fe594ee9b33d82058545b1ed14f4c8206e",
    "who": "tests-mozilla-inbound-ubuntu64_vm-opt-unittest",
    "failure_classification_id": 1,
    "job_type_symbol": "1",
    "reason": "scheduler",
    "job_group_description": "fill me",
    "tier": 1, "job_coalesced_to_guid": null,
    "machine_platform_os": "linux",
    "start_timestamp": 1435806437,
    "build_architecture": "x86_64",
    "device_name": "vm",
    "last_modified": "2015-07-02T03:29:09",
    "signature": "41f96d52f5fc013ae82825172d9e13f4e517c5ac"
}
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
        buildapi.JOBS_CACHE = {}
        query_jobs.JOBS_CACHE = {}

    @patch('requests.get', return_value=mock_response(JOBS_SCHEDULE, 200))
    @patch('mozci.sources.pushlog.valid_revision', return_value=True)
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    @patch('mozci.sources.buildapi.query_repo_url', return_value=None)
    def test_call_first_time(self, query_repo_url, get_credentials, valid_revision, get):
        """_get_all_jobs should return the right value after calling requests.get."""
        self.assertEquals(
            self.query_api._get_all_jobs("try", "146071751b1e"),
            json.loads(JOBS_SCHEDULE))

        assert get.call_count == 1

        # Test that this fills our caches
        self.assertEquals(
            query_jobs.JOBS_CACHE[("try", "146071751b1e")],
            json.loads(JOBS_SCHEDULE))

    @patch('requests.get', return_value=mock_response(JOBS_SCHEDULE, 200))
    @patch('mozci.sources.pushlog.valid_revision', return_value=True)
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    @patch('mozci.sources.buildapi.query_repo_url', return_value=None)
    def test_call_second_time(self, query_repo_url, get_credentials, valid_revision, get):
        """Calling the function again should return us the results directly from cache."""
        # Making sure the cache is filled so we don't depend on the order of the tests.
        query_jobs.JOBS_CACHE[("try", "146071751b1e")] = json.loads(JOBS_SCHEDULE)
        self.assertEquals(
            self.query_api._get_all_jobs("try", "146071751b1e"),
            json.loads(JOBS_SCHEDULE))
        # _get_all_jobs should return its value directly from
        # cache without calling get
        assert get.call_count == 0

    @patch('requests.get', return_value=mock_response(JOBS_SCHEDULE, 400))
    @patch('mozci.sources.pushlog.valid_revision', return_value=True)
    @patch('mozci.sources.buildapi.get_credentials', return_value=None)
    @patch('mozci.sources.buildapi.query_repo_url', return_value=None)
    def test_bad_request(self, query_repo_url, get_credentials, valid_revision, get):
        """If a bad return value is found in requests we should return an empty list."""
        self.assertEquals(
            self.query_api._get_all_jobs("try", "146071751b1e"), [])

    @patch('mozci.sources.pushlog.valid_revision', return_value=False)
    @patch('mozci.sources.buildapi.query_repo_url', return_value=None)
    def test_bad_revision(self, query_repo_url, valid_revision):
        """If an invalid revision is passed, _get_all_jobs should raise an Exception ."""
        print "****", buildapi.JOBS_CACHE, query_jobs.JOBS_CACHE
        with self.assertRaises(Exception):
            self.query_api._get_all_jobs("try", "146071751b1e")


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

    @patch('mozci.query_jobs.BuildApi._is_coalesced', return_value=SUCCESS)
    def test_successful_job(self, _is_coalesced):
        """Test get_job_status with a successful job. We will mock _is_coalesced for that."""
        successful_job = json.loads(BASE_JSON % (SUCCESS, 1433166610, 1, 1433166609))[0]
        self.assertEquals(self.query_api.get_job_status(successful_job), SUCCESS)

    @patch('mozci.query_jobs.BuildApi._is_coalesced', return_value=COALESCED)
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


class TestTreeherderApiGetJobStatus(unittest.TestCase):
    """Test query_job_status with different types of jobs"""

    def setUp(self):
        self.query_api = TreeherderApi()

    def test_pending_job(self):
        """Test TreeherderApi get_job_status with a successful job."""

        pending_job = json.loads(TREEHERDER_JOB % ("unknown", "pending"))
        self.assertEquals(self.query_api.get_job_status(pending_job), PENDING)

    def test_running_job(self):
        """Test TreeherderApi get_job_status with a successful job."""

        running_job = json.loads(TREEHERDER_JOB % ("unknown", "running"))
        self.assertEquals(self.query_api.get_job_status(running_job), RUNNING)

    def test_successful_job(self):
        """Test TreeherderApi get_job_status with a successful job."""

        successful_job = json.loads(TREEHERDER_JOB % ("success", "completed"))
        self.assertEquals(self.query_api.get_job_status(successful_job), SUCCESS)

    def test_failed_job(self):
        """Test TreeherderApi get_job_status with a successful job."""

        failed_job = json.loads(TREEHERDER_JOB % ("testfailed", "completed"))
        self.assertEquals(self.query_api.get_job_status(failed_job), FAILURE)

    def test_weird_job(self):
        """get_job_status should raise an Exception when it encounters an unexpected status."""
        weird_job = json.loads(TREEHERDER_JOB % ("weird", "null"))
        with self.assertRaises(TreeherderException):
            self.query_api.get_job_status(weird_job)


class TestBuildApiGetMatchingJobs(unittest.TestCase):

    def setUp(self):
        self.query_api = BuildApi()

    def test_matching_jobs_existing(self):
        """_matching_jobs should return the whole dictionary for a buildername in alljobs."""
        self.assertEquals(
            self.query_api.get_matching_jobs(
                "try", "146071751b1e",
                'Linux x86-64 try build'), json.loads(JOBS_SCHEDULE))

    def test_matching_jobs_invalid(self):
        """_matching_jobs should return an empty list if it receives an invalid buildername."""
        self.assertEquals(
            self.query_api.get_matching_jobs(
                "try", "146071751b1e",
                'Invalid buildername'), [])
