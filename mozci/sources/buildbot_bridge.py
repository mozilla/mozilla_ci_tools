"""
This module contains helper methods to help schedule tasks on TaskCluster
which will use the buildbot-bridge system to trigger them on buildbot.
"""
from __future__ import absolute_import

import json

from taskcluster.utils import slugId, fromNow

from mozci.sources.pushlog import query_revision_info
from mozci.sources.buildapi import query_repo_url
from mozci.mozci import query_repo_name_from_buildername

TREEHERDER_ROUTES = {
    'staging': 'tc-treeherder-stage',
    'production': 'tc-treeherder'
}


def _create_task(buildername, repo_name, revision, treeherder_route, metadata, requires=None):
    task = {
        'taskId': slugId(),
        'task': {
            'workerType': 'buildbot-bridge',
            'provisionerId': 'buildbot-bridge',
            'created': fromNow('0d'),
            'deadline': fromNow('1d'),
            'payload': {
                'buildername': buildername,
                'sourcestamp': {
                    'branch': repo_name,
                    'revision': revision
                },
                'properties': {
                    'product': 'firefox'
                }
            },
            'metadata': dict(metadata.items() + {'name': buildername}.items()),
            'extra': {
                # 'build_product': 'firefox',  # Is this needed?
                'treeherder': {  # What in here is needed?
                    'groupSymbol': 'tc',  # XXX: fix
                    'collection': {
                        'debug': True  # XXX: fix
                    },
                    'machine': {
                        'platform': 'windowsxp'  # XXX: fix
                    },
                    'groupName': 'Submitted by taskcluster',
                    'build': {
                        'platform': 'windowsxp'  # XXX: fix
                    },
                    'symbol': 'B'  # XXX: fix
                },
                'treeherderEnv': [
                    'production',
                    'staging'
                ]
            }
        }
    }

    if requires:
        task['requires'] = requires

    decorate_task_treeherder_routes(task['task'], treeherder_route)

    return task


def _query_metadata(repo_name, revision):
    repo_url = query_repo_url(repo_name)
    push_info = query_revision_info(repo_url, revision)

    return {
        'owner': push_info['user'],
        'source': '%s/rev/%s' % (repo_url, revision),
        'description': 'Task graph generated via Mozilla CI tools',
    }, {
        # https://treeherder.mozilla.org/api/project/try/resultset/?revision=b0af66e75fdd
        'revision_hash': 'a904ceceacd413be16a524f5c1cb7bcd15dcec5f'
    }


def _validate_builders_graph(repo_name, builders_graph):
    '''
    Helper function to validate that a builders_graph contains valid
    builders

    returns boolean
    '''
    result = True
    for builder, dep_builders in builders_graph.iteritems():
        if repo_name not in builder:
            result = False
            break
        for dep_builder in dep_builders:
            if repo_name not in dep_builder:
                result = False
                break

    return result


# From https://hg.mozilla.org/mozilla-central/file/default/testing/taskcluster/mach_commands.py#l115
def decorate_task_treeherder_routes(task, suffix):
    """
    Decorate the given task with treeherder routes.

    Uses task.extra.treeherderEnv if available otherwise defaults to only
    staging.

    :param dict task: task definition.
    :param str suffix: The project/revision_hash portion of the route.
    """
    if 'extra' not in task:
        return

    if 'routes' not in task:
        task['routes'] = []

    treeheder_env = task['extra'].get('treeherderEnv', ['staging'])

    for env in treeheder_env:
        task['routes'].append('{}.{}'.format(TREEHERDER_ROUTES[env], suffix))


def generate_task_graph(repo_name, revision, builders_graph, **params):
    '''
    revision       - push revision
    builders_graph - it is a graph made up of a dictionary where each key is
                     a Buildbot buildername. The value for each key is either
                     an empty list or a list of builders to trigger as
                     dependent jobs.

    return None or a valid taskcluster task graph.

    NOTE: All builders in the graph must contain the same repo_name.
    NOTE: The revision must be a valid one for the implied repo_name from the
          buildernames.
    '''
    if builders_graph is None:
        return None

    metadata, other_data = _query_metadata(repo_name, revision)
    repo_name = query_repo_name_from_buildername(builders_graph.keys()[0])
    treeherder_route = '{}.{}'.format(repo_name, other_data['revision_hash'])

    _validate_builders_graph(repo_name, builders_graph)

    # This is the initial task graph which we're defining
    task_graph = {
        'scopes': [
            'queue:define-task:buildbot-bridge/buildbot-bridge',
        ],
        'tasks': [],
        'metadata': dict(metadata.items() + {'name': 'task graph local'}.items())
    }

    if other_data['revision_hash']:
        for env in TREEHERDER_ROUTES:
            task_graph['scopes'].append(
                'queue:route:{}.{}'.format(TREEHERDER_ROUTES[env], treeherder_route))

    for builder, dependent_builders in builders_graph.iteritems():
        task = _create_task(
            buildername=builder,
            repo_name=repo_name,
            revision=revision,
            treeherder_route=treeherder_route,
            metadata=metadata
        )

        task_id = task['taskId']
        task_graph['tasks'].append(task)

        for dep_builder in dependent_builders:
            task = _create_task(
                buildername=dep_builder,
                repo_name=repo_name,
                revision=revision,
                treeherder_route=treeherder_route,
                metadata=metadata,
                requires=[task_id]
            )

            task_graph['tasks'].append(task)

    # We use standard json because ujson does not support 'indent'
    print(json.dumps(task_graph, indent=4))
    return task_graph
