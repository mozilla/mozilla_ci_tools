"""This file contains tests for mozci/ci_manager.py."""
import pytest

from mozci import (
    BuildAPIManager,
    TaskClusterBuildbotManager,
    TaskClusterManager,
)
from mozci.ci_manager import BaseCIManager


def test_initiate_base_class():
    with pytest.raises(TypeError):
        BaseCIManager()


def test_initiate_buildapi_manager():
    BuildAPIManager()


def test_initiate_taskcluster_buildbot_manager():
    TaskClusterBuildbotManager(dry_run=True)


def test_initiate_taskcluster_manager():
    TaskClusterManager(dry_run=True)
