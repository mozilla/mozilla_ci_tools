import json

from mozci.platforms import build_tests_per_platform_graph
from mozci.sources.allthethings import fetch_allthethings_data


if __name__ == '__main__':
    with open('graph.json', 'w') as f:
        builders = fetch_allthethings_data()['builders']
        graph = build_tests_per_platform_graph(builders)
        json.dump(graph, f, sort_keys=True, indent=4, separators=(',', ': '))
