"""This file contains tests for mozci/mozci.py with data from mock_allthethings.json"""
import json
import os
# import pytest
import unittest

from mock import patch

import mozci.sources.allthethings


def _get_mock_allthethings():
    """Load a mock allthethings.json from disk."""
    PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_allthethings.json")
    with open(PATH, 'r') as f:
        return json.load(f)

MOCK_ALLTHETHINGS = _get_mock_allthethings()


class TestSourcesAllTheThings(unittest.TestCase):

    """Test allthethings with mock data."""

    @patch('mozci.sources.allthethings.fetch_allthethings_data')
    def test_list_builders(self, fetch_allthethings_data):
        """is_dowstream should return True for test jobs and False for build jobs."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS

        expected_sorted = \
            [u'Platform1 mozilla-beta build',
             u'Platform1 mozilla-beta pgo talos tp5o',
             u'Platform1 mozilla-beta talos tp5o',
             u'Platform1 repo build',
             u'Platform1 repo debug test mochitest-1',
             u'Platform1 repo leak test build',
             u'Platform1 repo mochitest-1',
             u'Platform1 repo talos tp5o',
             u'Platform2 mozilla-beta build',
             u'Platform2 mozilla-beta talos tp5o']

        self.assertEquals(sorted(mozci.sources.allthethings.list_builders()), expected_sorted)
