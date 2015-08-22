"""
This module allow us to interact with taskcluster through the taskcluster
client.
"""
import datetime
import logging
import traceback

import taskcluster as taskcluster_client
import ujson as json

LOG = logging.getLogger('mozci')
TASKCLUSTER_TOOLS_HOST = 'https://tools.taskcluster.net'


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
    one_year = 365
    new_task_id = 0

    try:
        queue = taskcluster_client.Queue()
        task = queue.task(task_id)

        LOG.debug("Original task: (Limit 1024 char)")
        LOG.debug(str(json.dumps(task))[:1024])
        new_task_id = taskcluster_client.slugId()

        artifacts = task['payload'].get('artifacts', {})
        for artifact, definition in artifacts.iteritems():
            definition['expires'] = taskcluster_client.fromNow('%s days' % one_year)

        # The task group will be identified by the ID of the only
        # task in the group
        task['taskGroupId'] = new_task_id
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

        if not dry_run:
            LOG.info("Attempting to schedule new task with task_id: {}".format(new_task_id))
            result = queue.createTask(new_task_id, task)
            LOG.debug(json.dumps(result))
            LOG.info("{}/task-inspector/#{}".format(TASKCLUSTER_TOOLS_HOST, new_task_id))
        else:
            LOG.info("Dry-run mode: Nothing was retriggered.")

    except taskcluster_client.exceptions.TaskclusterRestFailure as e:
        traceback.print_exc()
        new_task_id = -1

    except taskcluster_client.exceptions.TaskclusterAuthFailure as e:
        # Hack until we fix it in the issue
        if str(e) == "Authorization Failed":
            LOG.error("The taskclaster client that you specified is lacking "
                      "the right set of scopes.")
            LOG.error("Run this same command with --debug and you will see "
                      "the missing scopes (the output comes from the "
                      "taskcluster python client)")
        elif str(e) == "Authentication Error":
            LOG.error("Make sure that you create permanent credentials and you "
                      "set these environment variables: TASKCLUSTER_CLIENT_ID & "
                      "TASKCLUSTER_ACCESS_TOKEN")
        new_task_id = -1

    return new_task_id
