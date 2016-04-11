"""This file contains the tests for mozci/sources/tc.py"""
import json
import unittest
import os

# 3rd party modules
from jsonschema.exceptions import ValidationError
from mock import Mock, patch

# Current tool
from mozci.sources.tc import (
    generate_metadata,
    validate_graph
)
from helpers import (
    debug_logging
)

debug_logging()
CWD = os.path.dirname(os.path.abspath(__file__))


class TestTaskClusterGraphs(unittest.TestCase):
    """Testing mozci integration with TaskCluster"""
    def setUp(self):
        with open(os.path.join(CWD, 'tc_test_graph.json')) as data_file:
            self.bad_graph = json.load(data_file)

        with open(os.path.join(CWD, 'tc_test_graph2.json')) as data_file:
            self.bad_graph_2 = json.load(data_file)

        with open(os.path.join(CWD, 'tc_test_graph3.json')) as data_file:
            self.good_graph = json.load(data_file)

    def test_check_invalid_graph(self):
        # This file lacks the "task" property under "tasks"
        self.assertRaises(ValidationError, validate_graph, self.bad_graph)

    def test_check_invalid_graph2(self):
        # This should fail as the owner's email ID is not valid
        self.assertRaises(ValidationError, validate_graph, self.bad_graph_2)

    def test_check_valid_graph(self):
        # Similar to the previous test, but with the correct owner field
        validate_graph(self.good_graph)
        self.assert_(True)


class TestTaskGeneration(unittest.TestCase):
    """Test that we can create tasks with expected values."""

    def setUp(self):
        self.revision = '1ab622ac1706a0f5dfaf7734a1c56aa9d3502eec'
        self.repo_name = 'try'
        self.repo_url = 'https://hg.mozilla.org/try'

        # Let's mock what Push object looks like
        node = Mock()
        node.node = u'1ab622ac1706a0f5dfaf7734a1c56aa9d3502eec'

        self.push_info = Mock()
        self.push_info.user = u'dminor@mozilla.com'
        self.push_info.changesets = [node]

    @patch('mozci.sources.tc.query_push_by_revision')
    @patch('mozci.sources.tc.query_repo_url')
    def test_metadata_contains_matches_name(self,
                                            query_repo_url,
                                            query_push_by_revision):
        ''' We want to test that the builder will show up in the name of the metadata.

        This helps when we look at tasks when inspecting a graph scheduled via BBB.
        See https://github.com/mozilla/mozilla_ci_tools/issues/444 for details.
        '''
        query_repo_url.return_value = self.repo_url
        query_push_by_revision.return_value = self.push_info

        builder = 'Platform1 try leak test build'
        metadata = {
            'name': builder,
            'description': 'Task graph generated via Mozilla CI tools',
            'owner': self.push_info.user,
            'source': u'%s/rev/%s' % (self.repo_url, self.revision)
        }

        self.assertEquals(
            generate_metadata(
                repo_name=self.repo_name,
                revision=self.revision,
                name=builder
            ),
            metadata
        )
