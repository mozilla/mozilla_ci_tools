''' Auxiliary module to help load mock_allthethings.json for all tests. '''
import logging
import json
import os

from mozci.utils.log_util import setup_logging


def _get_mock_allthethings():
    """Load a mock allthethings.json from disk."""
    PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "mock_allthethings.json"
    )
    with open(PATH, 'r') as f:
        return json.load(f)


def debug_logging():
    ''' Call this from a test and you will then be able to call py.test with -s'''
    setup_logging(logging.DEBUG)


MOCK_ALLTHETHINGS = _get_mock_allthethings()
