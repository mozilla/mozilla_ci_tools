"""This file contains tests for mozci/mozci.py."""

import json
import pytest
import unittest

import mozci.mozci
from mozci.sources import buildapi

from mock import patch

MOCK_JSON = '''{
                "real-repo": {
                    "repo": "https://hg.mozilla.org/integration/real-repo",
                    "graph_branches": ["Real-Repo"],
                    "repo_type": "hg"}}'''


class TestQueries(unittest.TestCase):

    """This class tests the functions query_repo_url and query_repository."""

    def setup_class(cls):
        """Replacing query_repositories with a mock function."""
        def mock_query_repositories(clobber=True):
            return json.loads(MOCK_JSON)

        buildapi.query_repositories = mock_query_repositories

    def test_query_repo_url_valid(self):
        """A repository in the JSON file must return the corresponding url."""
        assert mozci.mozci.query_repo_url('real-repo') == \
            "https://hg.mozilla.org/integration/real-repo"

    def test_query_repo_url_invalid(self):
        """A repository not in the JSON file must trigger an exception."""
        with pytest.raises(Exception):
            mozci.mozci.query_repo_url('not-a-repo')

    def test_query_repository_valid(self):
        """A repository in the JSON file return the corresponding dict."""
        assert mozci.mozci.query_repository('real-repo') == json.loads(MOCK_JSON)['real-repo']

    def test_query_repository_invalid(self):
        """A repository not in the JSON file must trigger an exception."""
        with pytest.raises(Exception):
            mozci.mozci.query_repository('not-a-repo')

    def test_query_repo_name_from_buildername_b2g(self):
        """Test query_repo_name_from_buildername with a b2g job."""
        self.assertEquals(
            mozci.mozci.query_repo_name_from_buildername("b2g_real-repo_win32_gecko build"),
            "real-repo")

    def test_query_repo_name_form_buildername_normal(self):
        """Test query_repo_name_from_buildername with a normal job."""
        self.assertEquals(
            mozci.mozci.query_repo_name_from_buildername("Linux real-repo opt build"),
            "real-repo")

    def test_query_repo_name_from_buildername_invalid(self):
        """If no repo name is found at the job, the function should raise an Exception."""
        with pytest.raises(Exception):
            mozci.mozci.query_repo_name_from_buildername("Linux not-a-repo opt build")


class TestJobValidation(unittest.TestCase):

    """Test functions that deal with alljobs."""
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

    def test_matching_jobs_existing(self):
        """_matching_jobs should return the whole dictionary for a buildername in alljobs."""
        assert mozci.mozci._matching_jobs('Platform repo test', self.alljobs) == self.jobs

    def test_matching_jobs_invalid(self):
        """_matching_jobs should return an empty list if it receives an invalid buildername."""
        assert mozci.mozci._matching_jobs('Invalid buildername', self.alljobs) == []

    @patch('mozci.sources.buildapi.BuildapiJobStatus.get_status',
           return_value=buildapi.SUCCESS)
    def test_status_summary_successful(self, get_status):
        """
        _status_summary depends on buildapi.query_job_status that uses buildjson.query_job_data.

        We will only test _status_summary with simple mocks of query_job_status here. This test
        is with a success state.
        """
        assert mozci.mozci._status_summary(self.jobs) == (1, 0, 0, 0)

    @patch('mozci.sources.buildapi.BuildapiJobStatus.get_status',
           return_value=buildapi.PENDING)
    def test_status_summary_pending(self, get_status):
        """Test _status_summary with a running state."""
        assert mozci.mozci._status_summary(self.jobs) == (0, 1, 0, 0)

    @patch('mozci.sources.buildapi.BuildapiJobStatus.get_status',
           return_value=buildapi.RUNNING)
    def test_status_summary_running(self, get_status):
        """Test _status_summary with a running state."""
        assert mozci.mozci._status_summary(self.jobs) == (0, 0, 1, 0)

    @patch('mozci.sources.buildapi.BuildapiJobStatus.get_status',
           return_value=buildapi.COALESCED)
    def test_status_summary_coalesced(self, get_status):
        """Test _status_summary with a coalesced state."""
        assert mozci.mozci._status_summary(self.jobs) == (0, 0, 0, 1)
