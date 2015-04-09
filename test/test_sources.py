"""This file contains tests for mozci/sources with data from mock_allthethings.json"""
import json
import unittest

from mock import patch

import mozci.sources.allthethings


class TestSourcesAllTheThings(unittest.TestCase):

    """Test mozci.sources with mock data."""

    @patch('mozci.sources.allthethings.fetch_allthethings_data')
    def test_list_builders_with_mock_data(self, fetch_allthethings_data):
        """list_builders should return list of builders from allthethings."""
        fetch_allthethings_data.return_value = json.loads("""
        {"builders" :
            {
            "Builder 1": {},
            "Builder 2": {}
            }
        }""")

        expected_sorted = [u'Builder 1', u'Builder 2']

        self.assertEquals(sorted(mozci.sources.allthethings.list_builders()), expected_sorted)

    @patch('mozci.sources.allthethings.fetch_allthethings_data')
    def test_list_builders_assert_on_empty_list(self, fetch_allthethings_data):
        """list_builders should raise AssertionError if there are no builders listed in allthethings."""
        fetch_allthethings_data.return_value = json.loads("""
        {
        "builders" : {},
        "schedulers":
            {
            "Scheduler 1": {},
            "Scheduler 2": {}
            }
        }""")
        with self.assertRaises(AssertionError):
            mozci.sources.allthethings.list_builders()
