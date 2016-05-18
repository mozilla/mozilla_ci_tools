"""This file contains tests for mozci/sources/buildbot_bridge.py."""
import unittest

from mock import Mock, patch

from mozci.sources.buildbot_bridge import (
    _create_task,
)

from helpers import (
    ALLTHETHINGS,
)


class TestBuildbotBridge(unittest.TestCase):
    """Test that buildbot bridge is correctly scheduling tasks"""
    def setUp(self):
        self.revision = '1ab622ac1706a0f5dfaf7734a1c56aa9d3502eec'
        self.repo_name = 'try'
        self.repo_url = 'https://hg.mozilla.org/try'

        node = Mock()
        node.node = u'1ab622ac1706a0f5dfaf7734a1c56aa9d3502eec'

        self.push_info = Mock()
        self.push_info.changesets = [node]

    @patch('mozci.platforms.fetch_allthethings_data', return_value=ALLTHETHINGS)
    @patch('mozci.sources.buildbot_bridge.query_push_by_revision')
    @patch('mozci.sources.buildbot_bridge.query_repo_url')
    @patch('mozci.sources.buildbot_bridge.valid_builder', return_value=True)
    def test_task_name_metadata_is_buildername(self,
                                               valid_builder,
                                               query_repo_url,
                                               query_push_by_revision,
                                               fetch_allthethings_data):
        ''' We want to test that the builder will show up in the metadata of a created task.

        This helps when we look at tasks when inspecting a graph scheduled via BBB.
        See https://github.com/mozilla/mozilla_ci_tools/issues/444 for details.
        '''
        query_push_by_revision.return_value = self.push_info
        query_repo_url.return_value = self.repo_url

        builder = 'WINNT 6.1 x86-64 try leak test build'
        metadata = {
            'owner': u'dminor@mozilla.com',
            'source': u'https://hg.mozilla.org/try/rev/1ab622ac1706a0f5dfaf7734a1c56aa9d3502eec',
            'name': builder,
            'description': 'Task graph generated via Mozilla CI tools'
        }

        task = _create_task(
            buildername=builder,
            repo_name=self.repo_name,
            revision=self.revision,
            metadata=metadata,
        )
        self.assertEquals(task['task']['metadata']['name'], builder)
