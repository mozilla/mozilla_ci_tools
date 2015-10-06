#! /usr/bin/env python
"""This module simply gives a logging functionality for all other modules to use."""
from __future__ import absolute_import

import logging

from mozci.utils.transfer import path_to_file

LOG = None


def setup_logging(level=logging.INFO):
    """
    Save every message (including debug ones) to ~/.mozilla/mozci/mozci-debug.log.

    Log messages of level equal or greater then 'level' to the terminal.

    As seen in:
    https://docs.python.org/2/howto/logging-cookbook.html#logging-to-multiple-destinations
    """
    global LOG
    if LOG:
        return LOG

    LOG = logging.getLogger("mozci")

    # Handler 1 - Store all debug messages in a specific file
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:\t %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S',
                        filename=path_to_file('mozci-debug.log'),
                        filemode='w')

    # Handler 2 - Console output
    console = logging.StreamHandler()
    console.setLevel(level)
    # console does not use the same formatter specified in basicConfig
    # we have to set it again
    formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s:\t %(message)s',
                                  datefmt='%m/%d/%Y %I:%M:%S')
    console.setFormatter(formatter)
    LOG.addHandler(console)

    if level != logging.DEBUG:
        # requests is too noisy and adds no value
        logging.getLogger("requests").setLevel(logging.WARNING)

    if level == logging.DEBUG:
        LOG.info("Setting DEBUG level")

    return LOG
