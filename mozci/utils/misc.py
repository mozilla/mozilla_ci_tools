#! /usr/bin/env python
"""This module simply adds miscellaneous code that the main modules can use."""
from __future__ import absolute_import
import logging

import requests

from mozci.utils.authentication import get_credentials
from mozci.utils.transfer import path_to_file

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


def setup_logging(level):
    """
    Save every message (including debug ones) to ~/.mozilla/mozci/mozci-debug.log.

    Log messages of level equal or greater then 'level' to the terminal.

    As seen in:
    https://docs.python.org/2/howto/logging-cookbook.html#logging-to-multiple-destinations
    """
    LOG = logging.getLogger('mozci')
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:\t %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S',
                        filename=path_to_file('mozci-debug.log'),
                        filemode='w')

    console = logging.StreamHandler()
    console.setLevel(level)
    # console does not use the same formatter specified in basicConfig
    # we have to set it again
    formatter = logging.Formatter('%(asctime)s %(levelname)s:\t %(message)s',
                                  datefmt='%m/%d/%Y %I:%M:%S')
    console.setFormatter(formatter)
    LOG.addHandler(console)

    if level != logging.DEBUG:
        # requests is too noisy and adds no value
        logging.getLogger("requests").setLevel(logging.WARNING)

    if level == logging.DEBUG:
        LOG.info("Setting DEBUG level")

    return LOG
