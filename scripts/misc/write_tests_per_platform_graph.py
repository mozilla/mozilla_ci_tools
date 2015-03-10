"""This script writes a mapping from platforms to tests that run in it to graph.json."""

import json

from mozci.platforms import build_tests_per_platform_graph, filter_builders_matching
from mozci.sources.allthethings import fetch_allthethings_data


if __name__ == '__main__':
    with open('graph.json', 'w') as f:
        builders = filter_builders_matching(fetch_allthethings_data()['builders'], "")
        graph = build_tests_per_platform_graph(builders)
        print 'Debug platforms: '
        for x in  sorted(graph['debug'].keys()):
            print x + ', ',
        print '\n Opt platforms:'
        for x in  sorted(graph['opt'].keys()):
            print x + ', ',
        json.dump(graph, f, sort_keys=True, indent=4, separators=(',', ': '))
