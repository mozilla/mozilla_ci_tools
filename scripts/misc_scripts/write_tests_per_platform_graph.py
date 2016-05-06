"""This script writes a mapping from platforms to tests that run in it to graph.json."""
import json

from mozci.platforms import build_tests_per_platform_graph, list_builders
from mozci.utils.transfer import path_to_file


if __name__ == '__main__':
    with open(path_to_file('graph.json'), 'w') as f:
        graph = build_tests_per_platform_graph(
            builders=list_builders())
        json.dump(graph, f, sort_keys=True, indent=4, separators=(',', ': '))
