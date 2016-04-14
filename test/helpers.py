''' Auxiliary module to help load mock_allthethings.json for all tests. '''
import json
import os


def _get_mock_allthethings():
    """Load a mock allthethings.json from disk."""
    PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "mock_allthethings.json"
    )
    with open(PATH, 'r') as f:
        return json.load(f)


MOCK_ALLTHETHINGS = _get_mock_allthethings()
