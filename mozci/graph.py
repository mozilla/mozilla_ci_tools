import collections
import json

from sources.allthethings import fetch_allthethings_data


def get_test(buildername):
    '''For test jobs, the test type is the last part of the name. For example:
    in Windows 7 32-bit mozilla-central pgo talos chromez-e10s
    the test type is chromez-e10s
    '''
    return buildername.split(" ")[-1]


def build_tests_per_platform_graph():
    builders = fetch_allthethings_data()['builders']
    graph = collections.defaultdict(list)

    for builder in builders:
        props = builders[builder]['properties']
        if 'slavebuilddir' in props and props['slavebuilddir'] == 'test':
            platform = builders[builder]['properties']['platform']

            # For talos tests we have to check stage_platform instead
            if 'talos' in builder:
                platform = builders[builder]['properties']['stage_platform']

            test = get_test(builder)
            if test not in graph[platform]:
                graph[platform].append(get_test(builder))

    for platform in graph:
        graph[platform].sort()

    return graph


with open('graph.json', 'w') as f:
    graph = build_tests_per_platform_graph()
    json.dump(graph, f, sort_keys=True, indent=4, separators=(',', ': '))
