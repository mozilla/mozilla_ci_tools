"""This file contains tests for mozci/sources/buildbot_bridge.py."""
import unittest
from mozci.sources import buildbot_bridge


class TestBuildbotBridge(unittest.TestCase):
    """Test that buildbot bridge is correctly scheduling tasks"""
    def setUp(self):
        self.buildernames = ['Android armv7 API 15+ try debug build']
        self.revision = '1ab622ac1706a0f5dfaf7734a1c56aa9d3502eec'
        self.repo_name = 'try'
        self.builders_graph, _ = buildbot_bridge.buildbot_graph_builder(
            builders=self.buildernames,
            revision=self.revision,
            complete=False
        )

    def test_task_name_metadata_is_buildername(self):
        self.graph = buildbot_bridge.generate_builders_tc_graph(
            self.repo_name,
            self.revision,
            self.builders_graph
        )
        flag = False
        for task in self.graph['tasks']:
            if task['task']['metadata']['name'] == self.buildernames[0]:
                flag = True
        self.assertEquals(flag, True)
