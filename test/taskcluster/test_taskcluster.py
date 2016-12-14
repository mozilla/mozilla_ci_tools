"""This file contains the tests for mozci/taskcluster/__init__.py"""
import json
import os
import unittest

# 3rd party modules
import pytest
from jsonschema.exceptions import ValidationError
from mock import Mock, patch

# Current tool
from mozci.taskcluster import (
    TC_SCHEMA_URL,
    TaskClusterManager,
    credentials_available,
    generate_metadata,
    validate_schema,
)

CWD = os.path.dirname(os.path.abspath(__file__))


# Beginning of fixtures


@pytest.fixture
def bad_graph1():
    with open(os.path.join(CWD, 'bad_graph1.json')) as data_file:
        return json.load(data_file)


@pytest.fixture
def bad_graph2():
    with open(os.path.join(CWD, 'bad_graph2.json')) as data_file:
        return json.load(data_file)


@pytest.fixture
def good_graph1():
    with open(os.path.join(CWD, 'good_graph1.json')) as data_file:
        return json.load(data_file)


@pytest.fixture
def tc_manager():
    return TaskClusterManager(dry_run=True)


@pytest.fixture
def good_action_old_style():
    with open(os.path.join(CWD, 'good_action_old_style.yml')) as data_file:
        return data_file.read()


@pytest.fixture
def good_action():
    with open(os.path.join(CWD, 'good_action.yml')) as data_file:
        return data_file.read()


#
# Beginning of tests
#
def test_credentials_available():
    os.environ['TASKCLUSTER_CLIENT_ID'] = 'fake'
    os.environ['TASKCLUSTER_ACCESS_TOKEN'] = 'fake'
    assert credentials_available() is True


class TestTaskClusterGraphs():
    def test_check_invalid_graph(self, bad_graph1):
        # This file lacks the "task" property under "tasks"
        with pytest.raises(ValidationError):
            validate_schema(instance=bad_graph1, schema_url=TC_SCHEMA_URL)

    def test_check_invalid_graph2(self, bad_graph2):
        # This should fail as the owner's email ID is not valid
        with pytest.raises(ValidationError):
            validate_schema(instance=bad_graph2, schema_url=TC_SCHEMA_URL)

    def test_check_valid_graph(self, good_graph1):
        # Similar to the previous test, but with the correct owner field
        validate_schema(instance=good_graph1, schema_url=TC_SCHEMA_URL)


class TestTaskClusterActionTask():
    def test_check_valid_action(self, tc_manager, good_action):
        task = json.loads(tc_manager.render_action_task(
            good_action,
            'action-task',
            'abc123',
            {'foo_bar': 'baz'}
        ))
        assert 'taskgraph action-task --foo-bar="baz"' in task['payload']['command'][-1]

    def test_check_valid_action_old_style(self, tc_manager, good_action_old_style):
        task = json.loads(tc_manager.render_action_task(
            good_action_old_style,
            'action-task',
            'abc123',
            {'task_labels': ['baz/bar']}
        ))
        assert ("taskgraph action-task --decision-id='abc123' --task-label='baz/bar'" in
                task['payload']['command'][-1])


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

    @patch('mozci.taskcluster.query_push_by_revision')
    @patch('mozci.taskcluster.query_repo_url')
    def test_metadata_contains_matches_name(self,
                                            query_repo_url,
                                            query_push_by_revision):
        ''' We want to test that the builder will show up in the name of the metadata.

        This helps when we look at tasks when inspecting a graph scheduled via BBB.
        See https://github.com/mozilla/mozilla_ci_tools/issues/444 for details.
        '''
        query_repo_url.return_value = self.repo_url
        query_push_by_revision.return_value = self.push_info

        builder = 'Platform1 mozilla-central leak test build'
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
