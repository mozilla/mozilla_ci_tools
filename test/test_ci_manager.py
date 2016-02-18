"""This file contains tests for mozci/ci_manager.py."""

import unittest

from mozci.ci_manager import BaseCIManager, BuildAPIManager, TaskClusterManager


class TestInstantiation(unittest.TestCase):
    """Test that classes are instanciated and do not fail to implement the base class."""

    def test_initiate_base_class(self):
        with self.assertRaises(TypeError):
            BaseCIManager()

    def test_initiate_buildapi_manager(self):
        BuildAPIManager()

    def test_initiate_taskcluster_manager(self):
        TaskClusterManager()
