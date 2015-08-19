"""
This module allow us to interact with the various scheduling systems
in a very generic manner.

Defined in here:
    * BaseSchedulingClient
    * TaskclusterSchedulingClient
"""
from __future__ import absolute_import

from abc import ABCMeta, abstractmethod

from mozci.sources import (
    buildapi,
    buildbot_bridge,
    tc
)


class BaseSchedulingClient:
    """ Base class for common scheduling methods. """

    __metaclass__ = ABCMeta

    @abstractmethod
    def schedule_arbitrary_task(self, repo_name, revision, uuid, *args, **kwargs):
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

# End of BaseSchedulingClient


class BuildAPISchedulingClient(BaseSchedulingClient):

    def schedule_arbitrary_task(self, repo_name, revision, uuid, *args, **kwargs):
        return buildapi.trigger_arbitrary_job(repo_name=repo_name,
                                              builder=uuid,
                                              revision=revision,
                                              *args,
                                              **kwargs)

    def retrigger(self, uuid, *args, **kwargs):
        return buildapi.make_retrigger_request(request_id=uuid, *args, **kwargs)

    def cancel(self, uuid, *args, **kwargs):
        return buildapi.make_cancel_request(
            repo_name=kwargs['repo_name'],
            request_id=uuid,
            *args,
            **kwargs)

    def cancel_all(self, repo_name, revision, *args, **kwargs):
        pass

# End of BuildAPISchedulingClient


class TaskclusterSchedulingClient(BaseSchedulingClient):

    def schedule_task_graph(self, task_graph):
        # XXX: We should call the tc client
        pass

    def schedule_arbitrary_task(self, repo_name, revision, uuid, *args, **kwargs):
        pass

    def retrigger(self, uuid, *args, **kwargs):
        return tc.retrigger_task(task_id=uuid, *args, **kwargs)

    def cancel(self, uuid, *args, **kwargs):
        pass

    def cancel_all(self, repo_name, revision, *args, **kwargs):
        pass
# End of TaskClusterSchedulingClient


class BBBSchedulingClient(TaskclusterSchedulingClient):

    def schedule_task_graph(self, repo_name, revision, builders_graph, *args, **kwargs):
        '''
        repo_name      - e.g. alder, mozilla-central
        revision       - push revision
        builders_graph - it is a graph made up of a dictionary where each key is
                         a Buildbot buildername. The value for each key is either
                         an empty list or another graph (to support multiple levels
                         of dependencies). The leaf nodes are lists.

        return None or a valid taskcluster task graph.

        NOTE: All builders in the graph must contain the same repo_name.
        NOTE: The revision must be a valid one for the implied repo_name from
              the buildernames.
        '''
        return buildbot_bridge.generate_task_graph(
            repo_name=repo_name,
            revision=revision,
            builders_graph=builders_graph,
            *args,
            **kwargs
        )

    def schedule_arbitrary_task(self, repo_name, revision, uuid, *args, **kwargs):
        task = buildbot_bridge.schedule_arbitrary_builder(
            revision=revision,
            buildername=uuid,
            *args, **kwargs
        )
        super(BBBSchedulingClient, self).schedule_arbitrary_task(task)
# End of BuildbotBridgeSchedulingClient
