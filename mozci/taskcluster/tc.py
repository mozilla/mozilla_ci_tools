"""
This module allow us to interact with taskcluster via the taskcluster client.
"""
from __future__ import absolute_import

import datetime
import json
import logging
import os
import yaml

# 3rd party modules
import requests
import taskcluster as taskcluster_client
from taskcluster.utils import slugId, fromNow
from jsonschema import (
    validate,
    FormatChecker
)

# This project
from mozci.ci_manager import BaseCIManager
from mozci.errors import (
    TaskClusterArtifactError,
    TaskClusterError
)
from mozci.repositories import query_repo_url
from mozhginfo.pushlog_client import query_push_by_revision


LOG = logging.getLogger(__name__)
TC_TOOLS_HOST = 'https://tools.taskcluster.net'
TC_TASK_INSPECTOR = "%s/task-inspector/#" % TC_TOOLS_HOST
TC_TASK_GRAPH_INSPECTOR = "%s/task-graph-inspector/#" % TC_TOOLS_HOST
TC_SCHEMA_URL = 'http://schemas.taskcluster.net/scheduler/v1/task-graph.json'
TC_INDEX_URL = 'https://index.taskcluster.net/v1/task/'
TC_QUEUE_URL = 'https://queue.taskcluster.net/v1/task/'


class TaskClusterManager(BaseCIManager):

    def __init__(self, credentials=None, web_auth=False, dry_run=False):
        ''' Initialize the authentication method.'''
        self.dry_run = dry_run

        if dry_run:
            self.queue = taskcluster_client.Queue()

        elif credentials_available():
            self.queue = taskcluster_client.Queue()

        elif credentials:
            self.queue = taskcluster_client.Queue({'credentials': credentials})

        elif web_auth:
            # Your browser will open a new tab asking you to authenticate
            # through TaskCluster and then grant access to this
            self.queue = taskcluster_client.Queue({'credentials': authenticate()})

        else:
            raise TaskClusterError(
                ""
                "Since you're not running in dry run mode, you need to provide "
                "an authentication method:\n"
                " 1) call authenticate() to get credentials and pass it as credentials.\n"
                " 2) set TASKCLUSTER_{CLIENT_ID,ACCESS_TOKEN} as env variables.\n"
                " 3) use web_auth=True to authenticate through your web browser.."
            )

    def schedule_graph(self, task_graph, *args, **kwargs):
        validate_schema(instance=task_graph, schema_url=TC_SCHEMA_URL)
        return schedule_graph(task_graph, *args, **kwargs)

    def schedule_task(self, task, update_timestamps=True, dry_run=False):
        """ It schedules a TaskCluster task

        For more details visit:
        http://docs.taskcluster.net/queue/api-docs/#createTask

        :param task: It is a TaskCluster task.
        :type task: json
        :param update_timestamps: It will not update the timestamps if False.
        :type update_timestamps: bool
        :param dry_run: It allows overwriting the dry_run mode at creation of the manager.
        :type dry_run: bool
        :returns: Task Status Structure (see link to createTask documentation)
        :rtype: dict

        """
        LOG.debug("We want to schedule a TC task")

        if update_timestamps:
            task = refresh_timestamps(task)

        # http://schemas.taskcluster.net/queue/v1/create-task-request.json#
        if not (dry_run or self.dry_run):
            # https://github.com/taskcluster/taskcluster-client.py#create-new-task
            task_id = taskcluster_client.slugId()
            result = self.queue.createTask(taskId=task_id, payload=task)
            LOG.info("Inspect the task in {}".format(get_task_inspector_url(task_id)))
            return result
        else:
            LOG.info("We did not schedule anything because we're running on dry run mode.")

    def schedule_action_task(self, action, decision_id, action_args=None):
        """
        Function which will be used to schedule an action task.
        Action Tasks use in-tree logic to schedule the task_labels
        """
        # Downloading the YAML file for action tasks
        # Action Tasks will be used to schedule the Task Labels in the parameters
        action_task = get_artifact_for_task_id(task_id=decision_id,
                                               artifact_path="public/action.yml")
        action_task = self.render_action_task(action_task, action, decision_id, action_args)
        self.schedule_task(task=json.loads(action_task))

    def render_action_task(self, action_task, action, decision_id, action_args):
        # Satisfying mustache template variables in YML file
        # We must account for both the old and new style of arg passing
        if "{{action_args}}" in action_task:
            action_args = [(k.replace('_', '-'), v) for k, v in action_args.items()]
            action_args = ['--{}="{}"'.format(k, v) for k, v in action_args]
            action_task = action_task.replace("{{action}}", action)
            action_task = action_task.replace("{{action_args}}", " ".join(action_args))
        else:
            action_task = action_task.replace("{{decision_task_id}}", decision_id)
            action_task = action_task.replace("{{task_labels}}", ",".join(
                action_args["task_labels"])
            )

        task = yaml.load(action_task)
        text = json.dumps(task, indent=4, sort_keys=True)
        return text

    def extend_task_graph(self, task_graph_id, task_graph, *args, **kwargs):
        return extend_task_graph(task_graph_id, task_graph, *args, **kwargs)

    def schedule_arbitrary_job(self, repo_name, revision, uuid, *args, **kwargs):
        pass

    def retrigger(self, uuid, *args, **kwargs):
        return retrigger_task(task_id=uuid, *args, **kwargs)

    def cancel(self, uuid, *args, **kwargs):
        pass

    def cancel_all(self, repo_name, revision, *args, **kwargs):
        pass

    def trigger_range(self, buildername, repo_name, revisions, times, dry_run, files,
                      trigger_build_if_missing):
        pass


# End of TaskClusterManager
def credentials_available():
    ''' Check if credentials variables have been set. We don't check their validity.
    '''
    if os.environ.get('TASKCLUSTER_CLIENT_ID', None) and \
       os.environ.get('TASKCLUSTER_ACCESS_TOKEN', None):

        LOG.debug("We have credentials set. We don't know if they're valid.")
        return True
    else:
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
    LOG.debug("Determining metadata.")
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


def get_task_inspector_url(task_id):
    return '{}{}'.format(TC_TASK_INSPECTOR, task_id)


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
        # Do not retry the task if it fails to run successfully
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


def refresh_timestamps(task):
    ''' It refreshes the timestamps of the task. '''
    # XXX split this function
    LOG.debug("Updating timestamps of task.")

    LOG.debug("Original task: (Limit 1024 char)")
    LOG.debug(str(json.dumps(task))[:1024])

    artifacts = task['payload'].get('artifacts', {})
    for artifact, definition in artifacts.iteritems():
        definition['expires'] = taskcluster_client.fromNow('%s days' % 365)

    # https://bugzilla.mozilla.org/show_bug.cgi?id=1190660
    # TC workers create public logs which are 365 days; if the task expiration
    # date is the same or less than that we won't have logs for the task
    task['expires'] = taskcluster_client.fromNow('%s days' % (365 + 1))
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
              of a successful retriggered task.

    http://docs.taskcluster.net/queue/api-docs/#createTask
    """
    if not credentials_available():
        return None

    results = None
    # XXX: evaluate this code for when we can still extend the graph
    #      insted of scheduling a new one
    try:
        # Copy the task with fresh timestamps
        original_task = get_task(task_id)
        new_task = refresh_timestamps(original_task)
        new_task['taskId'] = taskcluster_client.slugId()

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
            # https://github.com/taskcluster/taskcluster-client.py#create-new-task-graph
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


def validate_schema(instance, schema_url):
    """ This function tests the graph with a JSON schema
    """
    schema = requests.get(schema_url).json()

    # validate() does not return a value if valid, thus, not keeping track of it.
    validate(instance=instance, schema=schema, format_checker=FormatChecker())


def authenticate():
    """
    This function opens a browser and asks users to login
    using LDAP / Persona account. The user may then grant
    permissions to mozci to schedule tasks.
    """
    LOG.info("We're going to open a new tab and authenticate you with TaskCluster.")
    return taskcluster_client.authenticate()


def get_latest_full_task(repo_name="mozilla-inbound"):
    """
    This function fetches the latest full-task-graph file
    for a given repository.
    """
    namespace = "gecko.v2." + repo_name + ".latest.firefox.decision"
    full_tasks_url = TC_INDEX_URL + namespace + "/artifacts/public/full-task-graph.json"
    full_tasks = requests.get(full_tasks_url).json()
    return full_tasks


def get_artifact_for_task_id(task_id, artifact_path):
    """
    This is a generic function which downloads a TaskCluster artifact in plain text.
    """
    if task_id is None or len(task_id) == 0:
        raise TaskClusterError("Please input a valid Task ID to fetch the artifact.")
    url = TC_QUEUE_URL + task_id + "/artifacts/" + artifact_path
    resp = requests.get(url)
    if resp.status_code != 200:
        raise TaskClusterArtifactError("Please check your Task ID and artifact path.")
    return resp.text


def is_taskcluster_label(task_label, decision_task_id):
    """
    This function tests whether a given task label is valid for a decision task id.
    """
    full_task_text = get_artifact_for_task_id(task_id=decision_task_id,
                                              artifact_path="public/full-task-graph.json")
    full_task_graph = json.loads(full_task_text)
    return task_label in full_task_graph
