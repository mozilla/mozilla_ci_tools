"""This script writes a mapping from platforms to tests that run in it to graph.json."""

import json

from mozci.platforms import build_tests_per_platform_graph, _filter_builders_matching
from mozci.sources.allthethings import fetch_allthethings_data
from mozci.utils.transfer import path_to_file


if __name__ == '__main__':
    with open(path_to_file('graph.json'), 'w') as f:
        builders = _filter_builders_matching(fetch_allthethings_data()['builders'], " try ")
        graph = build_tests_per_platform_graph(builders)
        json.dump(graph, f, sort_keys=True, indent=4, separators=(',', ': '))
