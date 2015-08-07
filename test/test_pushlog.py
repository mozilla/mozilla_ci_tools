import json
import unittest

from mock import patch, Mock
from mozci.sources import pushlog


def mock_response(content):
    """Mock of requests.get()."""
    response = Mock()
    response.content = content

    def mock_response_json():
        return json.loads(content)

    response.json = mock_response_json
    return response

INVALID_REVISION = """
"unknown revision '123456123456s'"
"""

GOOD_REVISION = """
{
 "82366": {
  "changesets": [
   "4e030c8cf8c35158c9924f6bb33ffe8af00c162b"
  ],
  "date": 1438992451,
  "user": "nobody@mozilla.com"
 }
}
"""


class TestValidRevision(unittest.TestCase):

    """Test valid_revision mocking GET requests."""

    @patch('requests.get', return_value=mock_response(GOOD_REVISION))
    def test_valid_without_any_cache(self, get):
        """Calling the function without in-memory cache."""
        # Making sure the original cache is empty
        pushlog.VALID_CACHE = {}
        self.assertEquals(
            pushlog.valid_revision("try", "4e030c8cf8c3"), True)

        # The in-memory cache should be filed now
        self.assertEquals(
            pushlog.VALID_CACHE, {("try", "4e030c8cf8c3"): True})

    @patch('requests.get', return_value=mock_response(GOOD_REVISION))
    def test_in_memory_cache(self,  get):
        """Calling the function with in-memory cache should return without calling request.get."""
        pushlog.VALID_CACHE = {("try", "146071751b1e"): True}
        self.assertEquals(
            pushlog.valid_revision("try", "146071751b1e"), True)

        assert get.call_count == 0

    @patch('requests.get', return_value=mock_response(INVALID_REVISION))
    def test_invalid(self, get):
        """Calling the function with a bad revision."""
        self.assertEquals(
            pushlog.valid_revision("try", "123456123456"), False)
