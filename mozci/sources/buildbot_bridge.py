"""
This module contains helper methods to help schedule tasks on TaskCluster
which will use the buildbot-bridge system to trigger them on buildbot.

Instead of using LDAP credentials like for Buildapi, you need to have a set of credentials
with a couple of scopes for this purpose.

At this moment only a limited number of a Mozilla employee can create credentials for you:

* File a bug https://bugzilla.mozilla.org/enter_bug.cgi?product=Taskcluster&component=General
* CC armenzg or adusca to vouch for you
* Ask for your client to have the same scopes as this
* https://tools.taskcluster.net/auth/roles/#client-id:bbb-scheduler

After you receive your credentials you can specify your credentials with:

* export TASKCLUSTER_CLIENT_ID=<value>
* export TASKCLUSTER_ACCESS_TOKEN=<value>

You can use the script
https://github.com/mozilla/mozilla_ci_tools/blob/master/mozci/scripts/buildbot_to_taskcluster.py
to schedule Buildbot jobs via TaskCluster.
"""
from __future__ import absolute_import

import logging

from mozci.errors import MozciError
from mozci.mozci import determine_trigger_objective, valid_builder
from mozci.platforms import (
    is_downstream,
    is_upstream,
    get_buildername_metadata
)
from mozci.repositories import query_repo_url
from mozhginfo.pushlog_client import query_push_by_revision
from mozci.sources.tc import (
    get_task,
    get_task_graph_status,
    create_task,
    generate_task_graph,
    generate_metadata,
    schedule_graph,
    extend_task_graph,
)
from taskcluster.utils import slugId

LOG = logging.getLogger('mozci')


def _create_task(buildername, repo_name, revision, metadata=None, task_graph_id=None,
                 parent_task_id=None, requires=None, properties={}, *args, **kwargs):
    """Return takcluster task to trigger a buildbot builder.

    This function creates a generic task with the minimum amount of
    information required for the buildbot-bridge to consider it valid.
    You can establish a list dependencies to other tasks through the requires
    field.

    :param buildername: The name of a buildbot builder.
    :type buildername: str
    :param repo_name: The name of a repository e.g. mozilla-inbound
    :type repo_name: str
    :param revision: Changeset ID of a revision.
    :type revision: str
    :param metadata: Metadata for the task. If not specified, generate it.
    :type metadata: json
    :param task_graph_id: TC graph id to which this task belongs to
    :type task_graph_id: str
    :param parent_task_id: Task from which to find artifacts. It is not a dependency.
    :type parent_task_id: str
    :param requires: List of taskIds of other tasks which this task depends on.
    :type requires: list
    :returns: TaskCluster graph
    :rtype: dict

    """
    if not valid_builder(buildername):
        raise MozciError("The builder '%s' is not a valid one." % buildername)

    builder_info = get_buildername_metadata(buildername)
    if builder_info['repo_name'] != repo_name:
        raise MozciError(
            "The builder '%s' should be for repo: %s." % (buildername, repo_name)
        )

    repo_url = query_repo_url(repo_name)
    push_info = query_push_by_revision(repo_url=repo_url, revision=revision)
    full_revision = str(push_info.changesets[0].node)

    # Needed because of bug 1195751
    all_properties = {
        'product': builder_info['product'],
        'who': push_info.user,
    }
    all_properties.update(properties)

    metadata = metadata if metadata is not None else \
        generate_metadata(repo_name=repo_name,
                          revision=revision,
                          name=buildername)

    # XXX: We should validate that the parent task is a valid parent platform
    #      e.g. do not schedule Windows tests against Linux builds
    task = create_task(
        repo_name=repo_name,
        revision=revision,
        taskGroupId=task_graph_id,
        workerType='buildbot-bridge',
        provisionerId='buildbot-bridge',
        payload={
            'buildername': buildername,
            'sourcestamp': {
                'branch': repo_name,
                'revision': full_revision
            },
            'properties': all_properties,
        },
        metadata=metadata,
    )

    if requires:
        task['requires'] = requires

    # Setting a parent_task_id as a property allows Mozharness to
    # determine the artifacts we need for this job to run properly
    if parent_task_id:
        task['task']['payload']['properties']['parent_task_id'] = parent_task_id

    return task


def buildbot_graph_builder(builders, revision, complete=True):
    """ Return graph of builders based on a list of builders.

    # XXX: It would be better if had a BuildbotGraph class instead of messing
           with dictionaries.
           https://github.com/mozilla/mozilla_ci_tools/issues/353

    Input: a list of builders and a revision
    Output: a set which includes a graph with the builders we received, the necessary upstream
            jobs and list of builders which can been used to schedule jobs through trigger_job()

    NOTE: We will make it only return builder graph once Buildbot jobs are scheduled via
          the Buildbot Bridge (BBB) instead of the normal Buildbot scheduling.

    Graph of N levels:
        {
           'Builder a1': {
               'Builder a2': {
                   ...
                       'Builder aN': None
               },
           },
           'Builder b1': None
        }

    :param builders: List of builder names
    :type builders: list
    :param revision: push revision
    :type revision: str
    :return: A graph of buildernames (single level of graphs)
    :rtype: dict
    :param complete: indicate that build has been completed or not
    :type: booleans

    """
    graph = {}
    ready_to_trigger = []

    # We need to determine what upstream jobs need to be triggered besides the
    # builders already on our list
    for b in builders:
        if not valid_builder(buildername=b, quiet=True):
            continue

        if is_downstream(b):
            # For test jobs, determine_trigger_objective()[0] can be 3 things:
            # - the build job, if no build job exists
            # - the test job, if the build job is already completed
            # - None, if the build job is running
            objective = determine_trigger_objective(revision, b)[0]

            # The build job is already completed, we can trigger the test job
            if objective == b:
                # XXX: Fix me - Adding test jobs to the graph without a build associated
                # to it does not work. This will be fixed once we switch to scheduling
                # Buildbot jobs through BBB
                if complete:
                    graph[b] = None
                else:
                    ready_to_trigger.append(b)

            # The build job is running, there is nothing we can do
            elif objective is None:
                pass

            # We need to trigger the build job and the test job
            else:
                if objective not in graph:
                    graph[objective] = {}
                graph[objective][b] = None
        else:
            if b not in graph:
                graph[b] = {}

    # We might have left a build job poiting to an empty dict
    for builder in graph:
        if graph[builder] == {}:
            graph[builder] = None

    return graph, ready_to_trigger


def generate_tc_graph_from_builders(builders, repo_name, revision):
    """ Return TC graph based on a list of builders.

    :param builders: List of builder names
    :type builders: list
    :param repo_name: push revision
    :type repo_name: str
    :param revision: push revision
    :type revision: str
    :return: TC graph
    :rtype: dict

    """
    return generate_task_graph(
        scopes=[
            # This is needed to define tasks which take advantage of the BBB
            'queue:define-task:buildbot-bridge/buildbot-bridge',
        ],
        tasks=_generate_tc_tasks_from_builders(
            builders=builders,
            repo_name=repo_name,
            revision=revision
        ),
        metadata=generate_metadata(
            repo_name=repo_name,
            revision=revision,
            name='Mozci BBB graph'
        )
    )


def _generate_tc_tasks_from_builders(builders, repo_name, revision):
    """ Return TC tasks based on a list of builders.

    Input: a list of builders and a revision
    Output: list of TC tasks base on builders we receive

    :param builders: List of builder names
    :type builders: list
    :param repo_name: push revision
    :type repo_name: str
    :param revision: push revision
    :type revision: str
    :return: TC tasks
    :rtype: dict

    """
    tasks = []
    build_builders = {}

    # We need to determine what upstream jobs need to be triggered besides the
    # builders already on our list
    for builder in builders:
        if is_upstream(builder):
            task = _create_task(
                buildername=builder,
                repo_name=repo_name,
                revision=revision,
                # task_graph_id=task_graph_id,
                properties={'upload_to_task_id': slugId()},
            )
            tasks.append(task)

            # We want to keep track of how many build builders we have
            build_builders[builder] = task

    for builder in builders:
        if is_downstream(builder):
            # For test jobs, determine_trigger_objective()[0] can be 3 things:
            # - the build job, if no build job exists
            # - the test job, if the build job is already completed
            # - None, if the build job is running
            objective, package_url, tests_url = \
                determine_trigger_objective(revision, builder)

            # The build job is already completed, we can trigger the test job
            if objective == builder:
                if objective in build_builders:
                    LOG.warning("We're creating a new build even though there's "
                                "already an existing completed build we could have "
                                "used. We hope you wanted to do this.")
                    task = _create_task(
                        buildername=builder,
                        repo_name=repo_name,
                        revision=revision,
                        # task_graph_id=task_graph_id,
                        parent_task_id=build_builders[objective]['taskId'],
                        properties={'upload_to_task_id': slugId()},
                    )
                    tasks.append(task)
                else:
                    task = _create_task(
                        buildername=builder,
                        repo_name=repo_name,
                        revision=revision,
                        properties={
                            'packageUrl': package_url,
                            'testUrl': tests_url
                        },
                    )
                    tasks.append(task)

            # The build job is running, there is nothing we can do
            elif objective is None:
                LOG.warning("We can add %s builder since the build associated "
                            "is running. This is because it is a Buildbot job.")
                pass

            # We need to trigger the build job and the test job
            else:
                if objective not in build_builders:
                    task = _create_task(
                        buildername=builder,
                        repo_name=repo_name,
                        revision=revision,
                        # task_graph_id=task_graph_id,
                        properties={'upload_to_task_id': slugId()},
                    )
                    tasks.append(task)
                    taskId = task['taskId']
                else:
                    taskId = build_builders[objective]['taskId']

                # Add test job
                task = _create_task(
                    buildername=builder,
                    repo_name=repo_name,
                    revision=revision,
                    # task_graph_id=task_graph_id,
                    parent_task_id=taskId,
                )
                tasks.append(task)

    return tasks


def generate_graph_from_builders(repo_name, revision, buildernames, *args, **kwargs):
    """Return TaskCluster graph based on a list of buildernames.

    :param repo_name The name of a repository e.g. mozilla-inbound
    :type repo_name: str
    :param revision: push revision
    :type revision: str
    :param buildernames: List of Buildbot buildernames
    :type buildernames: list

    :returns: return None or a valid taskcluster task graph.
    :rtype: dict

    """
    return generate_builders_tc_graph(
        repo_name=repo_name,
        revision=revision,
        builders_graph=buildbot_graph_builder(buildernames, revision)[0])


def generate_builders_tc_graph(repo_name, revision, builders_graph, *args, **kwargs):
    """Return TaskCluster graph based on builders_graph.

    NOTE: We currently only support depending on one single parent.

    :param repo_name The name of a repository e.g. mozilla-inbound
    :type repo_name: str
    :param revision: push revision
    :type revision: str
    :param builders_graph:
        It is a graph made up of a dictionary where each
        key is a Buildbot buildername. The value for each key is either None
        or another graph of dependent builders.
    :type builders_graph: dict
    :returns: return None or a valid taskcluster task graph.
    :rtype: dict

    """
    if builders_graph is None:
        return None
    metadata = kwargs.get('metadata')
    if metadata is None:
        metadata = generate_metadata(repo_name=repo_name,
                                     revision=revision,
                                     name='Mozci BBB graph')
    # This is the initial task graph which we're defining
    task_graph = generate_task_graph(
        scopes=[
            # This is needed to define tasks which take advantage of the BBB
            'queue:define-task:buildbot-bridge/buildbot-bridge',
        ],
        tasks=_generate_tasks(
            repo_name=repo_name,
            revision=revision,
            builders_graph=builders_graph
        ),
        metadata=metadata
    )

    return task_graph


def _generate_tasks(repo_name, revision, builders_graph, metadata=None, task_graph_id=None,
                    parent_task_id=None, required_task_ids=[], **kwargs):
    """ Generate a TC json object with tasks based on a graph of graphs of buildernames

    :param repo_name: The name of a repository e.g. mozilla-inbound
    :type repo_name: str
    :param revision: Changeset ID of a revision.
    :type revision: str
    :param builders_graph:
        It is a graph made up of a dictionary where each
        key is a Buildbot buildername. The value for each key is either None
        or another graph of dependent builders.
    :type builders_graph: dict
    :param metadata: Metadata information to set for the tasks.
    :type metadata: json
    :param task_graph_id: TC graph id to which this task belongs to
    :type task_graph_id: str
    :param parent_task_id: Task from which to find artifacts. It is not a dependency.
    :type parent_task_id: int
    :returns: A dictionary of TC tasks
    :rtype: dict

    """
    if not type(required_task_ids) == list:
        raise MozciError("required_task_ids must be a list")

    tasks = []

    if type(builders_graph) != dict:
        raise MozciError("The buildbot graph should be a dictionary")

    # Let's iterate through the root builders in this graph
    for builder, dependent_graph in builders_graph.iteritems():
        # Due to bug 1221091 this will be used to know to which task
        # the artifacts will be uploaded to
        upload_to_task_id = slugId()
        task = _create_task(
            buildername=builder,
            repo_name=repo_name,
            revision=revision,
            metadata=metadata,
            task_graph_id=task_graph_id,
            parent_task_id=parent_task_id,
            properties={'upload_to_task_id': upload_to_task_id},
            requires=required_task_ids,
            **kwargs
        )
        task_id = task['taskId']
        tasks.append(task)

        if dependent_graph:
            # If there are builders this builder triggers let's add them as well
            tasks = tasks + _generate_tasks(
                repo_name=repo_name,
                revision=revision,
                builders_graph=dependent_graph,
                metadata=metadata,
                task_graph_id=task_graph_id,
                # The parent task id is used to find artifacts; only one can be given
                parent_task_id=upload_to_task_id,
                # The required tasks are the one holding this task from running
                required_task_ids=[task_id],
                **kwargs
            )

    return tasks


def trigger_builders_based_on_task_id(repo_name, revision, task_id, builders,
                                      *args, **kwargs):
    """ Create a graph of tasks which will use a TC task as their parent task.

    :param repo_name The name of a repository e.g. mozilla-inbound
    :type repo_name: str
    :param revision: push revision
    :type revision: str
    :returns: Result of scheduling a TC graph
    :rtype: dict

    """
    if not builders:
        return None

    if type(builders) != list:
        raise MozciError("builders must be a list")

    # If the task_id is of a task which is running we want to extend the graph
    # instead of submitting an independent one
    task = get_task(task_id)
    task_graph_id = task['taskGroupId']
    state = get_task_graph_status(task_graph_id)
    builders_graph, _ = buildbot_graph_builder(builders, revision)

    if state == "running":
        required_task_ids = [task_id]
    else:
        required_task_ids = []

    task_graph = generate_task_graph(
        scopes=[
            # This is needed to define tasks which take advantage of the BBB
            'queue:define-task:buildbot-bridge/buildbot-bridge',
        ],
        tasks=_generate_tasks(
            repo_name=repo_name,
            revision=revision,
            builders_graph=builders_graph,
            # This points to which parent to grab artifacts from
            parent_task_id=task_id,
            # This creates dependencies on other tasks
            required_task_ids=required_task_ids,
        ),
        metadata=generate_metadata(
            repo_name=repo_name,
            revision=revision,
            name='Mozci BBB graph'
        )
    )

    if state == "running":
        result = extend_task_graph(task_graph_id, task_graph)
    else:
        result = schedule_graph(task_graph, *args, **kwargs)

    LOG.info("Result from scheduling: %s" % result)
    return result
