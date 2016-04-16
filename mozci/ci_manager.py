"""
This module allow us to interact with the various scheduling systems
in a very generic manner.

Defined in here:
    * BaseCIManager
    * BuildAPIManager
    * TaskclusterManager
    * TaskClusterBuildbotManager
"""
from __future__ import absolute_import

from abc import ABCMeta, abstractmethod

from buildapi_client import (
    make_cancel_request,
    make_retrigger_request,
    make_retrigger_build_request,
    trigger_arbitrary_job
)

from mozci.platforms import list_builders
from mozci.mozci import trigger_range
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

    @abstractmethod
    def trigger_range(self, buildername, repo_name, revisions, times, dry_run, files,
                      trigger_build_if_missing):
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

    def retrigger_build(self, uuid, *args, **kwargs):
        return make_retrigger_build_request(build_id=uuid,
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

    def trigger_missing_jobs_for_revision(self, repo_name, revision, dry_run=False,
                                          trigger_build_if_missing=True):
        """
        Trigger missing jobs for a given revision.
        Jobs containing 'b2g' or 'pgo' in their buildername will not be triggered.
        """
        builders_for_repo = list_builders(repo_name=repo_name)

        for buildername in builders_for_repo:
            trigger_range(
                buildername=buildername,
                revisions=[revision],
                times=1,
                dry_run=dry_run,
                extra_properties={
                    'mozci_request': {
                        'type': 'trigger_missing_jobs_for_revision'
                    }
                },
                trigger_build_if_missing=trigger_build_if_missing
            )

    def trigger_range(self, buildername, repo_name, revisions, times, dry_run, files,
                      trigger_build_if_missing):
        trigger_range(
            buildername=buildername,
            revisions=revisions,
            times=times,
            dry_run=dry_run,
            files=files,
            trigger_build_if_missing=trigger_build_if_missing
        )

# End of BuildAPIManager
