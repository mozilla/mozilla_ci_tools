"""This file contains tests for mozci/sources/allthethings.py."""
import json
import os
import unittest

from mock import patch, Mock

from mozci.sources import allthethings


TMP_FILENAME = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "tmp_allthethings.json")


def mock_get(data):
    response = Mock()

    def iter_content(chunk_size=4):
        rest = data
        while rest:
            chunk = rest[:chunk_size]
            rest = rest[chunk_size:]
            yield chunk

    response.headers = {'content-length': str(len(data))}
    response.iter_content = iter_content
    return response


class TestFetching(unittest.TestCase):

    """Test fetch_allthethings_data() mocking requests."""

    allthethings.FILENAME = TMP_FILENAME
    DATA = '{"data": 1}'

    def setUp(self):
        """Setting up values that will be used in every test."""
        self.URL = "https://secure.pub.build.mozilla.org/builddata/reports/allthethings.json"

    def tearDown(self):
        """Clean up after every test."""
        if os.path.exists(TMP_FILENAME):
            os.remove(TMP_FILENAME)
        # This will clean in-memory caching
        allthethings.DATA = None

    @patch('requests.get', return_value=mock_get(DATA))
    @patch('requests.head', return_value=Mock(headers={'content-length': str(len(DATA))}))
    def test_calling_twice_with_caching(self, head, get):
        """
        We are going to call fetch_allthethings_data 2 times.

        The first time it should use requests.get to download the file, and requests.head
        to verify its integrity. The second time it will the file stored in-memory,
        so it won't call neither head or get.
        """
        # Calling the function the first time, and checking its result
        self.assertEquals(allthethings.fetch_allthethings_data(), {'data': 1})

        # Calling again
        allthethings.fetch_allthethings_data()
        get.assert_called_with(self.URL, stream=True)
        assert get.call_count == 1
        head.assert_called_with(self.URL)
        assert head.call_count == 1

    @patch('requests.get', return_value=mock_get(DATA))
    @patch('requests.head', return_value=Mock(headers={'content-length': str(len(DATA))}))
    def test_calling_twice_without_caching(self, head, get):
        """Without caching, get and head should both be called 2 times."""
        self.assertEquals(allthethings.fetch_allthethings_data(no_caching=True), {'data': 1})
        head.assert_called_with(self.URL)
        get.assert_called_with(self.URL, stream=True)

        # Calling again
        self.assertEquals(allthethings.fetch_allthethings_data(no_caching=True), {'data': 1})
        assert get.call_count == 2
        assert head.call_count == 2

    @patch('requests.get', return_value=mock_get(DATA))
    @patch('requests.head', return_value=Mock(headers={'content-length': str(len(DATA))}))
    def test_calling_with_bad_cache(self, head, get):
        """If the existing file is bad, we should download a new one."""
        # Making sure the cache exists and it's bad
        with open(TMP_FILENAME, 'w') as f:
            f.write('bad file')

        self.assertEquals(allthethings.fetch_allthethings_data(), {'data': 1})
        head.assert_called_with(self.URL)
        get.assert_called_with(self.URL, stream=True)

    def test_with_verify_set_to_false_and_existing_cache(self):
        """If verify is set to False and there already is a file, we should just use it."""
        # Making sure the file exists.
        with open(TMP_FILENAME, 'w') as f:
            f.write('{"data": 2}')
        self.assertEquals(allthethings.fetch_allthethings_data(verify=False), {'data': 2})

    def test_with_verify_set_to_false_and_no_cache(self):
        """If verify is set to False and there is no file, it should raise an Error."""
        with self.assertRaises(AssertionError):
            allthethings.fetch_allthethings_data(verify=False)


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

        self.assertEquals(sorted(allthethings.list_builders()), expected_sorted)

    @patch('mozci.sources.allthethings.fetch_allthethings_data')
    def test_list_builders_assert_on_empty_list(self, fetch_allthethings_data):
        """list_builders should raise AssertionError if there are no builders listed."""
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
            allthethings.list_builders()
