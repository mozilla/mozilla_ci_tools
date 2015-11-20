"""
This module allow us to interact with the various scheduling systems
in a very generic manner.

Defined in here:
    * BaseCIManager
    * BuildAPIManager
    * TaskclusterManager
"""
from __future__ import absolute_import

from abc import ABCMeta, abstractmethod

from buildapi_client import (
    make_cancel_request,
    make_retrigger_request,
    trigger_arbitrary_job
)

from mozci.sources import (
    buildbot_bridge,
    tc
)
from mozci.utils.authentication import get_credentials


class BaseCIManager:
    """ Base class for common interactions with our continuos integration systems. """

    __metaclass__ = ABCMeta

    @abstractmethod
    def schedule_arbitrary_job(self, repo_name, revision, uuid, *args, **kwargs):
        pass

    @abstractmethod
    def schedule_graph(self, repo_name, revision, uuid, *args, **kwargs):
        pass

    @abstractmethod
    def retrigger(self, uuid, *args, **kwargs):
        pass

    @abstractmethod
    def cancel(self, uuid, *args, **kwargs):
        pass

    @abstractmethod
    def cancel_all(self, repo_name, revision, *args, **kwargs):
        pass

# End of BaseCIManager


class BuildAPIManager(BaseCIManager):

    # BuildAPI does not support this
    def schedule_graph(self, repo_name, revision, uuid, *args, **kwargs):
        pass

    def schedule_arbitrary_job(self, repo_name, revision, uuid, *args, **kwargs):
        return trigger_arbitrary_job(repo_name=repo_name,
                                     builder=uuid,
                                     revision=revision,
                                     auth=get_credentials(),
                                     *args,
                                     **kwargs)

    def retrigger(self, uuid, *args, **kwargs):
        return make_retrigger_request(request_id=uuid,
                                      auth=get_credentials(),
                                      *args,
                                      **kwargs)

    def cancel(self, uuid, *args, **kwargs):
        return make_cancel_request(
            repo_name=kwargs['repo_name'],
            request_id=uuid,
            auth=get_credentials(),
            *args,
            **kwargs)

    def cancel_all(self, repo_name, revision, *args, **kwargs):
        pass

# End of BuildAPIManager


class TaskclusterManager(BaseCIManager):

    def schedule_graph(self, task_graph, *args, **kwargs):
        return tc.schedule_graph(task_graph, *args, **kwargs)

    def extend_task_graph(self, task_graph_id, task_graph, *args, **kwargs):
        return tc.extend_task_graph(task_graph_id, task_graph, *args, **kwargs)

    def schedule_arbitrary_job(self, repo_name, revision, uuid, *args, **kwargs):
        pass

    def retrigger(self, uuid, *args, **kwargs):
        return tc.retrigger_task(task_id=uuid, *args, **kwargs)

    def cancel(self, uuid, *args, **kwargs):
        pass

    def cancel_all(self, repo_name, revision, *args, **kwargs):
        pass

# End of TaskClusterManager


class TaskClusterBuildbotManager(TaskclusterManager):
    """ It is similar to the TaskClusterManager but it can only schedule buildbot jobs."""

    def schedule_graph(self, repo_name, revision, builders_graph, *args, **kwargs):
        """ It schedules a task graph for buildbot jobs through TaskCluster.

        Given a graph of Buildbot builders a TaskCluster graph will be generated
        which the Buildbot bridge will use to schedule Buildbot jobs.

        NOTE: All builders in the graph must contain the same repo_name.
        NOTE: The revision must be a valid one for the implied repo_name from
              the buildernames.

        :param repo_name: e.g. alder, mozilla-central
        :type repo_name: str
        :param revision: 12-chars representing a push
        :type revision: str
        :param builders_graph: It is a graph made up of a dictionary where each
                               key is a Buildbot buildername. The values to each
                               key are lists of builders (or empty list for build
                               jobs without test jobs).
        :type builders_graph: dict
        :returns: None or a valid taskcluster task graph.
        :rtype: dict

        """
        task_graph = buildbot_bridge.generate_builders_tc_graph(
            repo_name=repo_name,
            revision=revision,
            builders_graph=builders_graph,
        )
        return super(TaskClusterBuildbotManager, self).schedule_graph(
            task_graph=task_graph, *args, **kwargs)

    def schedule_arbitrary_job(self, repo_name, revision, uuid, *args, **kwargs):
        task_graph = buildbot_bridge.generate_graph_from_builders(
            repo_name=repo_name,
            revision=revision,
            buildernames=[uuid],
            *args, **kwargs
        )
        return super(TaskClusterBuildbotManager, self).schedule_graph(
            task_graph=task_graph, *args, **kwargs)

# End of TaskClusterBuildbotManager
