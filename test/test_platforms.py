"""This file contains tests for mozci/platforms.py."""
import json
import os
import pytest
import unittest

from mock import patch

import mozci.sources.allthethings
import mozci.platforms


def _get_mock_allthethings():
    """Load a mock allthethings.json from disk."""
    PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_allthethings.json")
    with open(PATH, 'r') as f:
        return json.load(f)

MOCK_ALLTHETHINGS = _get_mock_allthethings()


class TestIsDownstream(unittest.TestCase):

    """Test is_downstream with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_valid(self, fetch_allthethings_data):
        """is_dowstream should return True for test jobs and False for build jobs."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        self.assertEquals(mozci.platforms.is_downstream('Platform1 repo mochitest-1'), True)
        self.assertEquals(mozci.platforms.is_downstream('Platform1 repo build'), False)

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_invalid(self, fetch_allthethings_data):
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        with pytest.raises(Exception):
            mozci.platforms.determine_upstream_builder("Not a valid buildername")


class TestFindBuildernames(unittest.TestCase):

    """Test find_buildernames with mock data."""
    @patch('mozci.platforms.fetch_allthethings_data')
    def test_full(self, fetch_allthethings_data):
        """The function should return a list with the specific buildername."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        self.assertEquals(
            mozci.platforms.find_buildernames('repo', platform='platform1', test='mochitest-1'),
            ['Platform1 repo mochitest-1'])

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_without_platform(self, fetch_allthethings_data):
        """The function should return a list with all platforms for that test."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        self.assertEquals(
            sorted(mozci.platforms.find_buildernames('mozilla-beta', test='tp5o')),
            ['Platform1 mozilla-beta pgo talos tp5o',
             'Platform1 mozilla-beta talos tp5o',
             'Platform2 mozilla-beta talos tp5o'])

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_without_test(self, fetch_allthethings_data):
        """The function should return a list with all tests for that platform."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        self.assertEquals(
            mozci.platforms.find_buildernames('mozilla-beta', platform='stage-platform2'),
            ['Platform2 mozilla-beta talos tp5o'])

    def test_invalid(self):
        """The function should raise an error if both platform and test are None."""
        with pytest.raises(Exception):
            mozci.platforms.find_buildernames('repo', test=None, platform=None)


class TestGetPlatform(unittest.TestCase):

    """Test get_associated_platform_name with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_with_test_job(self, fetch_allthethings_data):
        """For non-talos test jobs it should return the platform attribute."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        self.assertEquals(
            mozci.platforms.get_associated_platform_name('Platform1 repo mochitest-1'), 'platform1')

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_talos(self, fetch_allthethings_data):
        """For talos jobs it should return the stage-platform attribute."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        self.assertEquals(
            mozci.platforms.get_associated_platform_name('Platform1 repo talos tp5o'),
            'stage-platform1')

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_with_build_job(self, fetch_allthethings_data):
        """For build jobs it should return the platform attribute."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        self.assertEquals(
            mozci.platforms.get_associated_platform_name('Platform1 repo build'), 'platform1')


class TestBuildGraph(unittest.TestCase):

    """Test build_tests_per_platform_graph."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_build_graph(self, fetch_allthethings_data):
        """Test if the graph has the correct format."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        builders = mozci.platforms._filter_builders_matching(MOCK_ALLTHETHINGS['builders'].keys(),
                                                             ' repo ')
        expected = {
            'debug': {'platform1':
                      {'tests': ['mochitest-1'],
                       'Platform1 repo leak test build':
                       ['Platform1 repo debug test mochitest-1']}},
            'opt': {'platform1':
                    {'tests': ['mochitest-1', 'tp5o'],
                     'Platform1 repo build':
                     ['Platform1 repo mochitest-1',
                      'Platform1 repo talos tp5o']}}}

        self.assertEquals(mozci.platforms.build_tests_per_platform_graph(builders), expected)


class TestDetermineUpstream(unittest.TestCase):

    """Test determine_upstream_builder with mock data."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_valid(self, fetch_allthethings_data):
        """Test if the function finds the right builder."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        self.assertEquals(
            mozci.platforms.determine_upstream_builder('Platform1 repo mochitest-1'),
            'Platform1 repo build')
        self.assertEquals(
            mozci.platforms.determine_upstream_builder('Platform1 repo debug test mochitest-1'),
            'Platform1 repo leak test build')
        self.assertEquals(
            mozci.platforms.determine_upstream_builder('Platform1 mozilla-beta pgo talos tp5o'),
            'Platform1 mozilla-beta build')
        # Since "Platform2 mozilla-beta pgo talos tp5o" does not exist,
        # "Platform2 mozilla-beta talos tp5o" is a valid buildername
        self.assertEquals(
            mozci.platforms.determine_upstream_builder('Platform2 mozilla-beta talos tp5o'),
            'Platform2 mozilla-beta build')

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_invalid(self, fetch_allthethings_data):
        """The function should raise an Exception buildernames not in allthethings.json."""
        fetch_allthethings_data.return_value = MOCK_ALLTHETHINGS
        with pytest.raises(Exception):
            mozci.platforms.determine_upstream_builder("Not a valid buildername")
        # Since "Platform1 mozilla-beta pgo talos tp5o" exists, "Platform1 mozilla-beta talos tp5o"
        # is an invalid buildername and should return None
        self.assertEquals(
            mozci.platforms.determine_upstream_builder("Platform1 mozilla-beta talos tp5o"),
            None)


class TestTalosBuildernames(unittest.TestCase):

    """We need this class because of the mock module."""

    @patch('mozci.platforms.fetch_allthethings_data')
    def test_talos_buildernames(self, fetch_allthethings_data):
        """Test build_talos_buildernames_for_repo with mock data."""
        fetch_allthethings_data.return_value = {
            'builders':
            {'PlatformA try talos buildername': {},
             'PlatformB try talos buildername': {},
             'PlatformA try pgo talos buildername': {},
             'Platform try buildername': {}}}
        self.assertEquals(mozci.platforms.build_talos_buildernames_for_repo('try'),
                          ['PlatformA try talos buildername',
                           'PlatformB try talos buildername'])
        self.assertEquals(mozci.platforms.build_talos_buildernames_for_repo('try', True),
                          ['PlatformA try pgo talos buildername',
                           'PlatformB try talos buildername'])
        self.assertEquals(mozci.platforms.build_talos_buildernames_for_repo('not-a-repo'), [])


get_test_test_cases = [
    ("Windows 8 64-bit mozilla-aurora pgo talos dromaeojs", "dromaeojs"),
    ("Android 2.3 Emulator mozilla-release opt test plain-reftest-7", "plain-reftest-7")]


@pytest.mark.parametrize("test, expected", get_test_test_cases)
def test_get_test(test, expected):
    """Test _get_test with test cases from get_test_test_cases."""
    obtained = mozci.platforms._get_test(test)
    assert obtained == expected, \
        'obtained: "%s", expected "%s"' % (obtained, expected)


def test_filter_builders_matching():
    """Test that _filter_builders_matching correctly filters builds."""
    BUILDERS = ["Ubuntu HW 12.04 mozilla-aurora talos svgr",
                "Ubuntu VM 12.04 b2g-inbound debug test xpcshell"]
    obtained = mozci.platforms._filter_builders_matching(BUILDERS, " talos ")
    expected = ["Ubuntu HW 12.04 mozilla-aurora talos svgr"]
    assert obtained == expected, \
        'obtained: "%s", expected "%s"' % (obtained, expected)
