"""
This module allow us to interact with taskcluster through the taskcluster
client.
"""
from __future__ import absolute_import

import datetime
import json
import logging
import os
import requests

import taskcluster as taskcluster_client
from taskcluster.utils import slugId, fromNow

from mozci.repositories import query_repo_url
from mozhginfo.pushlog_client import query_push_by_revision

from jsonschema import (
    validate,
    FormatChecker
)

LOG = logging.getLogger('mozci')
TC_TOOLS_HOST = 'https://tools.taskcluster.net'
TC_TASK_INSPECTOR = "%s/task-inspector/#" % TC_TOOLS_HOST
TC_TASK_GRAPH_INSPECTOR = "%s/task-graph-inspector/#" % TC_TOOLS_HOST


def credentials_available():
    ''' Check if credentials variables have been set. We don't check their validity.
    '''
    if os.environ.get('TASKCLUSTER_CLIENT_ID', None) and \
       os.environ.get('TASKCLUSTER_ACCESS_TOKEN', None):

        LOG.debug("We have credentials set. We don't know if they're valid.")
        return True
    else:
        LOG.error(
            "Make sure that you create permanent credentials and you "
            "set these environment variables: TASKCLUSTER_CLIENT_ID & "
            "TASKCLUSTER_ACCESS_TOKEN"
        )
        return False


def handle_exception(e):
    # Hack until we fix it in the issue
    if "Authorization Failed" in str(e):
        LOG.error("The TaskCluster client that you specified is lacking "
                  "the right set of scopes.")
        # After https://github.com/taskcluster/taskcluster-client.py/pull/48 lands
        # we will be able to output extra information
        # We can remove this error line at that point
        LOG.error("Run this same command with --debug and you will see "
                  "the missing scopes (the output comes from the "
                  "taskcluster python client)")
        LOG.exception(e)
    elif "Authentication Error" in str(e):
        LOG.error("Make sure that you create permanent credentials and you "
                  "set these environment variables: TASKCLUSTER_CLIENT_ID & "
                  "TASKCLUSTER_ACCESS_TOKEN")
        LOG.debug(str(e))
    else:
        LOG.exception(e)


def generate_metadata(repo_name, revision, name,
                      description='Task graph generated via Mozilla CI tools'):
    """ Generate metadata based on input
    :param repo_name: e.g. alder, mozilla-central
    :type repo_name: str
    :param revision: 12-chars representing a push
    :type revision: str
    :param name: Human readable name of task-graph, give people finding this an idea
                 what this graph is about.
    :type name: str
    :param description: Human readable description of task-graph, explain what it does!
    :type description: str
    """
    repo_url = query_repo_url(repo_name)
    push_info = query_push_by_revision(repo_url=repo_url,
                                       revision=revision)

    return {
        'name': name,
        'description': description,
        'owner': push_info.user,
        'source': '%s/rev/%s' % (repo_url, revision),
    }


def get_task(task_id):
    """ Returns task information for given task id.
    """
    queue = taskcluster_client.Queue()
    task = queue.task(task_id)
    LOG.debug("Original task: (Limit 1024 char)")
    LOG.debug(str(json.dumps(task))[:1024])
    return task


def get_task_graph_status(task_graph_id):
    """ Returns state of a Task-Graph Status Response
    """
    scheduler = taskcluster_client.Scheduler()
    response = scheduler.status(task_graph_id)
    return response['status']['state']


def create_task(**kwargs):
    """ Create a TC task.

    NOTE: This code needs to be tested for normal TC tasks to determine
    if the default values would also work for non BBB tasks.
    """
    task_id = kwargs.get('taskId', slugId())

    task_definition = {
        'taskId': task_id,
        # Do not retry the task if it fails to run successfuly
        'reruns': kwargs.get('reruns', 0),
        'task': {
            'workerType': kwargs['workerType'],  # mandatory
            'provisionerId': kwargs['provisionerId'],  # mandatory
            'created': kwargs.get('created', fromNow('0d')),
            'deadline': kwargs.get('deadline', fromNow('1d')),
            'expires': kwargs.get('deadline', fromNow('1d')),
            'payload': kwargs.get('payload', {}),
            'metadata': kwargs['metadata'],  # mandatory
            'schedulerId': kwargs.get('schedulerId', 'task-graph-scheduler'),
            'tags': kwargs.get('tags', {}),
            'extra': kwargs.get('extra', {}),
            'routes': kwargs.get('routes', []),
            'priority': kwargs.get('priority', 'normal'),
            'retries': kwargs.get('retries', 5),
            'scopes': kwargs.get('scopes', []),
        }
    }

    if kwargs.get('taskGroupId'):
        task_definition['task']['taskGroupId'] = kwargs.get('taskGroupId', task_id),

    return task_definition


def _recreate_task(task_id):
    one_year = 365
    queue = taskcluster_client.Queue()
    task = queue.task(task_id)

    LOG.debug("Original task: (Limit 1024 char)")
    LOG.debug(str(json.dumps(task))[:1024])

    # Start updating the task
    task['taskId'] = taskcluster_client.slugId()

    artifacts = task['payload'].get('artifacts', {})
    for artifact, definition in artifacts.iteritems():
        definition['expires'] = taskcluster_client.fromNow('%s days' % one_year)

    # https://bugzilla.mozilla.org/show_bug.cgi?id=1190660
    # TC workers create public logs which are 365 days; if the task expiration
    # date is the same or less than that we won't have logs for the task
    task['expires'] = taskcluster_client.fromNow('%s days' % (one_year + 1))
    now = datetime.datetime.utcnow()
    tomorrow = now + datetime.timedelta(hours=24)
    task['created'] = taskcluster_client.stringDate(now)
    task['deadline'] = taskcluster_client.stringDate(tomorrow)

    LOG.debug("Contents of new task: (Limit 1024 char)")
    LOG.debug(str(task)[:1024])

    return task


def retrigger_task(task_id, dry_run=False):
    """ Given a task id (our uuid) we  query it and build
    a new task based on the old one which we schedule on TaskCluster.

    We don't call the rerun API since we can't rerun a task past
    its deadline, instead we create a new task with a new taskGroupId,
    expiration, creation and deadline values.

    task_id (int)  - ID that identifies a task on Taskcluster
    dry_run (bool) - Default to False. If True, it won't trigger
                     a task.

    returns - 0 for dry_run case, -1 for any failure or the task id (int)
              of a succesful retriggered task.

    http://docs.taskcluster.net/queue/api-docs/#createTask
    """
    if not credentials_available():
        return None

    results = None
    # XXX: evaluate this code for when we can still extend the graph
    #      insted of scheduling a new one
    try:
        # Copy the task with fresh timestamps
        new_task = _recreate_task(task_id)

        # Create the graph
        task_graph = generate_task_graph(
            scopes=[],
            tasks=[new_task],
            metadata=new_task['metadata']
        )

        if not dry_run:
            LOG.info("Attempting to schedule new graph")
            results = schedule_graph(task_graph)
        else:
            LOG.info("Dry-run mode: Nothing was retriggered.")

    except Exception as e:
        handle_exception(e)

    return results


def schedule_graph(task_graph, task_graph_id=None, dry_run=False, *args, **kwargs):
    """ It schedules a TaskCluster graph and returns its id.

    :param task_graph: It is a TaskCluster graph as defined in here:
        http://docs.taskcluster.net/scheduler/api-docs/#createTaskGraph
    :type task_graph: json
    :param task_graph_id: TC graph id to which this task belongs to
    :type task_graph_id: str
    :param dry_run: It does not schedule the graph
    :type dry_run: bool
    :returns: task graph id.
    :rtype: int

    """
    if not task_graph_id:
        task_graph_id = taskcluster_client.slugId()
    scheduler = taskcluster_client.Scheduler()

    LOG.info("Outputting the graph (graph id: %s):" % task_graph_id)
    # We print to stdout instead of using the standard logging with dates and info levels
    # XXX: Use a different formatter for other tools to work better with this code
    print(json.dumps(task_graph, indent=4))
    if dry_run:
        LOG.info("DRY-RUN: We have not scheduled the graph.")
    else:
        if not credentials_available():
            return None

        try:
            result = scheduler.createTaskGraph(task_graph_id, task_graph)
            LOG.info("See the graph in %s%s" % (TC_TASK_GRAPH_INSPECTOR, task_graph_id))
            return result
        except Exception as e:
            handle_exception(e)


def extend_task_graph(task_graph_id, task_graph, dry_run=False):
    """

    From: http://docs.taskcluster.net/scheduler/api-docs/#extendTaskGraph

    Safety, it is only safe to call this API end-point while the task-graph
    being modified is still running. If the task-graph is finished or blocked,
    this method will leave the task-graph in this state. Hence, it is only
    truly safe to call this API end-point from within a task in the task-graph
    being modified.

    returns Task-Graph Status Response
    """
    # XXX: handle the case when the task-graph is not running
    scheduler = taskcluster_client.Scheduler()
    if dry_run:
        LOG.info("DRY-RUN: We have not extended the graph.")
    else:
        LOG.debug("When extending a graph we don't need metadata and scopes.")
        del task_graph['metadata']
        del task_graph['scopes']
        print(json.dumps(task_graph, indent=4))
        return scheduler.extendTaskGraph(task_graph_id, task_graph)


def generate_task_graph(scopes, tasks, metadata):
    """ It creates a TC task graph ready to be scheduled.
    """
    if 'scheduler:create-task-graph' not in scopes:
        scopes.append('scheduler:create-task-graph')

    # XXX: We could do validation in here
    task_graph = {
        'scopes': scopes,
        'tasks': tasks,
        'metadata': metadata
    }
    return task_graph


def validate_graph(graph):
    """ This function tests the graph with a JSON schema
    """
    schema = requests.get('http://schemas.taskcluster.net/scheduler/v1/task-graph.json').json()

    # validate() does not return a value if valid, thus, not keeping track of it.
    validate(instance=graph, schema=schema, format_checker=FormatChecker())
