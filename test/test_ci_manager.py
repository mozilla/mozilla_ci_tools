"""This file contains tests for mozci/ci_manager.py."""
import pytest

from mock import patch

from mozci import (
    BuildAPIManager,
    TaskClusterBuildbotManager,
    TaskClusterManager,
)
from mozci.ci_manager import BaseCIManager


def test_initiate_base_class():
    with pytest.raises(TypeError):
        BaseCIManager()

def test_initiate_taskcluster_buildbot_manager():
    TaskClusterBuildbotManager(dry_run=True)


def test_initiate_taskcluster_manager():
    TaskClusterManager(dry_run=True)


@pytest.fixture
def buildapi_manager():
    return BuildAPIManager()


class TestBuildAPIManager():
    def test_schedule_graph(self, buildapi_manager):
        # The function only calls 'pass'
        buildapi_manager.schedule_graph(
            repo_name='foo',
            revision='bar',
            uuid='moo',
        )

    @pytest.mark.skip(reason="This test only increases coverage but does not really test much.")
    @patch('mozci.ci_manager.get_credentials', return_value=None)
    def test_schedule_arbitrary_job(self, get_credentials, buildapi_manager):
        buildapi_manager.schedule_arbitrary_job(
            repo_name='foo',
            revision='bar',
            uuid='moo',
            dry_run=True
        )
