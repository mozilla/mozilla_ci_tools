#! /usr/bin/env python
"""This module simply gives a logging functionality for all other modules to use."""
from __future__ import absolute_import

import logging

from mozci.utils.transfer import path_to_file

LOG = None


def setup_logging(level=logging.INFO, datefmt='%I:%M:%S', show_timestamps=True,
                  show_name_level=False, requests_output=False):
    """ It helps set up mozci's logging and makes it easy to customize.

    It returns a cached logger if already called once.

    By default:
    * It logs INFO messages
    * It sets the default datefmt
    * It sets to show the timestamps of the messages
    * It does not show the messages level name (e.g. 'DEBUG')
    * It mutes INFO messages of the requests package since it is noisy
    * It logs messages of level equal or greater than 'level' to the terminal.
    * It also saves every message (including debug ones) to ~/.mozilla/mozci/mozci-debug.log.

    :param level: It sets which level messages to log
    :type level: int
    :param datefmt: It sets the format of the timestamps
    :type datefmt: str
    :param show_timestamps: It determines if to show the timestamps
    :type show_timestamps: bool
    :param show_name_level: It determines if to show the level name
    :type show_name_level: bool
    :param requests_output: It determines if to show logging of requests below the WARNING level
    :type requests_output: bool
    :returns: cached logger
    :rtype: logging.LOGGER

    As seen in:
    https://docs.python.org/2/howto/logging-cookbook.html#logging-to-multiple-destinations
    """
    global LOG
    if LOG:
        return LOG

    # We need to set the root logger or we will not see messages from dependent
    # modules
    LOG = logging.getLogger()

    format = ''
    if show_timestamps:
        format += '%(asctime)s '

    format += '%(name)s'

    if show_name_level:
        format += ' %(levelname)s '

    format += '\t%(message)s'

    # Handler 1 - Store all debug messages in a specific file
    logging.basicConfig(level=logging.DEBUG,
                        format=format,
                        datefmt=datefmt,
                        filename=path_to_file('mozci-debug.log'),
                        filemode='w')

    # Handler 2 - Console output
    console = logging.StreamHandler()
    console.setLevel(level)
    # console does not use the same formatter specified in basicConfig
    # we have to set it again
    formatter = logging.Formatter(format, datefmt=datefmt)
    console.setFormatter(formatter)
    LOG.addHandler(console)
    LOG.info("Setting %s level" % logging.getLevelName(level))

    if not requests_output:
        # requests is too noisy and adds no value
        # Set the value to warning to show actual issues
        logging.getLogger("requests").setLevel(logging.WARNING)

    return LOG
