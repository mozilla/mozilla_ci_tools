"""
This module contains helper methods to help schedule tasks on TaskCluster
which will use the buildbot-bridge system to trigger them on buildbot.
"""
from __future__ import absolute_import

import json

from taskcluster.utils import slugId, fromNow

from mozci.mozci import query_repo_name_from_buildername
from mozci.sources.buildapi import query_repo_url
from mozci.sources.pushlog import query_revision_info


def _create_task(buildername, repo_name, revision, metadata, requires=None):
    task = {
        'taskId': slugId(),
        'reruns': 0,  # Do not retry the task if it fails to run successfuly
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
                # Needed because of bug 1195751
                'properties': {
                    'product': 'firefox',  # XXX fix
                    'who': metadata['owner']
                }
            },
            'metadata': dict(metadata.items() + {'name': buildername}.items()),
        }
    }

    if requires:
        task['requires'] = requires

    return task


def _query_metadata(repo_name, revision):
    repo_url = query_repo_url(repo_name)
    push_info = query_revision_info(repo_url, revision)

    return {
        'owner': push_info['user'],
        'source': '%s/rev/%s' % (repo_url, revision),
        'description': 'Task graph generated via Mozilla CI tools',
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

    metadata = _query_metadata(repo_name, revision)
    repo_name = query_repo_name_from_buildername(builders_graph.keys()[0])

    _validate_builders_graph(repo_name, builders_graph)

    # This is the initial task graph which we're defining
    task_graph = {
        'scopes': [
            'queue:define-task:buildbot-bridge/buildbot-bridge',
        ],
        'tasks': [],
        'metadata': dict(metadata.items() + {'name': 'task graph local'}.items())
    }

    for builder, dependent_builders in builders_graph.iteritems():
        task = _create_task(
            buildername=builder,
            repo_name=repo_name,
            revision=revision,
            metadata=metadata
        )

        task_id = task['taskId']
        task_graph['tasks'].append(task)

        for dep_builder in dependent_builders:
            task = _create_task(
                buildername=dep_builder,
                repo_name=repo_name,
                revision=revision,
                metadata=metadata,
                requires=[task_id]
            )

            task_graph['tasks'].append(task)

    # We use standard json because ujson does not support 'indent'
    print(json.dumps(task_graph, indent=4))
    return task_graph
