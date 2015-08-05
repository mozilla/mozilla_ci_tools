"""
This module allow us to interact with the various scheduling systems
in a very generic manner.

Defined in here:
    * BaseSchedulingClient
    * TaskclusterSchedulingClient
"""
from __future__ import absolute_import
from abc import ABCMeta, abstractmethod

import mozci.sources.tc


class BaseSchedulingClient:
    """ Base class for common scheduling methods. """

    __metaclass__ = ABCMeta

    @abstractmethod
    def retrigger(self, uuid, **kwargs):
        pass


class TaskclusterSchedulingClient(BaseSchedulingClient):

    def retrigger(self, uuid, **kwargs):
        return tc.retrigger_task(task_id=uuid, **kwargs)
