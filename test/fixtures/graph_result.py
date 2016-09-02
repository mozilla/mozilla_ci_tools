from mozci.platforms import (
    build_tests_per_platform_graph,
    list_builders
)
import json
print json.dumps(
    build_tests_per_platform_graph(
        list_builders(repo_name='try')
    ),
    indent=4,
    sort_keys=True
)
