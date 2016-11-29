''' Auxiliary module to help load mock_allthethings.json for all tests. '''
import json
import os


def _get_allthethings():
    """Loads allthethings.json from disk."""
    PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "fixtures/allthethings.json"
    )
    with open(PATH, 'r') as f:
        return json.load(f)


def _get_SETA():
    """Loads SETA_result.json from disk."""
    PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "fixtures/SETA_result.json"
    )
    with open(PATH, 'r') as f:
        return json.load(f)


def _get_graph_result():
    """Loads graph_result.json from disk."""
    PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "fixtures/graph_result.json"
    )
    with open(PATH, 'r') as f:
        return json.load(f)


ALLTHETHINGS = _get_allthethings()


SETA_RESULT = _get_SETA()


GRAPH_RESULT = _get_graph_result()
