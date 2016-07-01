import pytest
from mock import patch

from mozci.utils.misc import _all_urls_reachable

# XXX: We could also patch requests.head to speed things up
@pytest.mark.parametrize("urls,result", [
    (["https://github.com/mozilla/mozilla_ci_tools", "https://github.com/mozilla/404"], False),
    (["https://github.com/mozilla/mozilla_ci_tools"], True),
])
@patch('mozci.utils.misc.get_credentials')
def test_not_all_urls_are_reachable(get_credentials, urls, result):
    get_credentials.return_value = ('', '')
    assert _all_urls_reachable(urls=urls) == result
