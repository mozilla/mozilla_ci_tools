#! /usr/bin/env python
"""This module simply adds miscellaneous code that the main modules can use."""
from __future__ import absolute_import
import logging

import requests

from mozci.utils.authentication import get_credentials

LOG = logging.getLogger('mozci')


def _public_url(url):
    """
    If we run the script outside the Release Engineering infrastructure
    we need to use the public interface rather than the internal one.
    """
    replace_urls = [
        ("http://pvtbuilds.pvt.build",
         "https://pvtbuilds"),
        ("http://tooltool.pvt.build.mozilla.org/build",
         "https://secure.pub.build.mozilla.org/tooltool/pvt/build")
    ]
    for from_, to_ in replace_urls:
        if url.startswith(from_):
            new_url = url.replace(from_, to_)
            LOG.debug("Replacing url %s ->\n %s" % (url, new_url))
            return new_url
    return url


def _all_urls_reachable(urls):
    """Determine if the URLs are reachable."""
    for url in urls:
        url_tested = _public_url(url)
        LOG.debug("We are going to test if we can reach %s" % url_tested)
        req = requests.head(url_tested, auth=get_credentials())
        if not req.ok:
            LOG.warning("We can't reach %s for this reason %s" %
                        (url, req.reason))
            return False

    return True
