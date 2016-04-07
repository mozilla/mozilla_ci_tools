from __future__ import absolute_import

import logging

from abc import ABCMeta, abstractmethod

from buildapi_client import query_jobs_schedule
from thclient import TreeherderClient

from mozci.errors import TreeherderError, BuildapiError, BuildjsonError
from mozci.utils.authentication import get_credentials
from mozci.platforms import list_builders
from mozci.sources.buildjson import query_job_data


LOG = logging.getLogger('mozci')
# Self-serve cannot give us the whole granularity of states; Use buildjson where necessary.
# http://hg.mozilla.org/build/buildbot/file/0e02f6f310b4/master/buildbot/status/builder.py#l25
PENDING, RUNNING, COALESCED, UNKNOWN = range(-4, 0)
SUCCESS, WARNING, FAILURE, SKIPPED, EXCEPTION, RETRY, CANCELLED = range(7)
JOBS_CACHE = {}


class QueryApi(object):
    """ Base class for common query methods """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_all_jobs(self, repo_name, revision):
        pass

    @abstractmethod
    def get_matching_jobs(self, repo_name, revision, buildername):
        pass

    @abstractmethod
    def get_buildapi_request_id(self, repo_name, job):
        pass

    @abstractmethod
    def get_job_status(self, job):
        pass

    def determine_missing_jobs(self, repo_name, revision, considered_list_of_builders=None):
        if considered_list_of_builders is None:
            considered_list_of_builders = list_builders(repo_name=repo_name)
        considered_list_of_builders = set(considered_list_of_builders)
        coalesced_jobs = self._select_jobs_with_specified_status(
            repo_name=repo_name,
            revision=revision,
            status=COALESCED,
            considered_list_of_builders=considered_list_of_builders)

        missing_jobs = self._select_missing_jobs(
            repo_name=repo_name,
            revision=revision,
            considered_list_of_builders=considered_list_of_builders)
        return missing_jobs + coalesced_jobs

    def _select_missing_jobs(self, repo_name, revision, considered_list_of_builders):
        all_jobs = self.get_all_jobs(repo_name, revision)
        for job in all_jobs:
            buildername = job["buildername"]
            try:
                considered_list_of_builders.remove(buildername)
            except KeyError:
                pass
        return list(considered_list_of_builders)

    def _select_jobs_with_specified_status(
            self, repo_name, revision, status, considered_list_of_builders=None):
        """
        Removes all buildernames from considered_list_of_builders whos job status
        isn't 'status'.

        :param repo_name The name of a repository e.g. mozilla-inbound
        :type repo_name: str
        :param revision: push revision
        :type revision: str
        :param status: job status e.g. COALESCED
        :type revision: int
        :param considered_list_of_builders: list of builders, can be used as a way to not consider
                                            all possible builders for a repository since many
                                            builders are not scheduled (e.g. pgo build jobs on
                                            inbound)
        :type revision: list
        :returns: Returns a list with the buildernames of the jobs whose 'status' is specified.
        :rtype: list

        """
        all_jobs = self.get_all_jobs(repo_name, revision)
        wrong_status_builders = set()
        correct_status_builders = set()
        for job in all_jobs:
            buildername = job["buildername"]
            try:
                if self.get_job_status(job) != status:
                    wrong_status_builders.add(buildername)
                else:
                    if buildername in considered_list_of_builders:
                        correct_status_builders.add(buildername)
            except BuildjsonError:
                LOG.info('We were not able to find status information for "%s"'
                         % buildername)

        correct_status_builders = correct_status_builders - wrong_status_builders
        return list(correct_status_builders)


class BuildApi(QueryApi):

    def get_all_jobs(self, repo_name, revision, use_cache=True):
        """
        Return a list with all jobs for that revision.

        If we can't query about this revision in buildapi_client we return an empty list.
        """
        if not use_cache:
            JOBS_CACHE[(repo_name, revision)] = \
                query_jobs_schedule(repo_name, revision, auth=get_credentials())

        if (repo_name, revision) not in JOBS_CACHE:
            JOBS_CACHE[(repo_name, revision)] = \
                query_jobs_schedule(repo_name, revision, auth=get_credentials())

        return JOBS_CACHE[(repo_name, revision)]

    def invalidate_jobs_cache(self):
        global JOBS_CACHE
        JOBS_CACHE = {}

    def get_buildapi_request_id(self, repo_name, job):
        """ Method to return buildapi's request_id for a job. """
        # Most jobs have a "requests" key, but sometimes there is just
        # a "request_id" key.
        if "requests" in job:
            return job["requests"][0]["request_id"]
        return job["request_id"]

    def get_matching_jobs(self, repo_name, revision, buildername):
        """Return all jobs that matched the criteria."""
        LOG.debug("Find jobs matching '%s'" % buildername)
        all_jobs = self.get_all_jobs(repo_name, revision)
        matching_jobs = []
        for j in all_jobs:
            if j["buildername"] == buildername:
                matching_jobs.append(j)

        LOG.debug("We have found %d job(s) of '%s'." %
                  (len(matching_jobs), buildername))
        return matching_jobs

    def get_job_status(self, job):
        """
        Helper to determine the scheduling status of a job from self-serve.

        Raises BuildapiError on an unexpected status.
        """
        if "status" not in job:
            return PENDING

        status = job["status"]
        if status is None:
            if job.get("endtime") is None:
                return RUNNING
            return UNKNOWN

        if status in (WARNING, FAILURE, EXCEPTION, RETRY, CANCELLED):
            return status

        if status == SUCCESS:
            # The success status for self-serve can actually be a coalesced job
            return self._is_coalesced(job)

        LOG.debug(job)
        raise BuildapiError("Unexpected status")

    def _is_coalesced(self, job):
        """Helper method to determine if a job with status 'SUCCESS' is coalesced.
           Bug: https://bugzilla.mozilla.org/show_bug.cgi?id=1175611
        """
        assert job["status"] == SUCCESS

        req = job["requests"][0]
        status_data = query_job_data(req["complete_at"], req["request_id"])
        if not status_data:
            LOG.info("We have not found the job. We assume the job to be running.")
            return RUNNING

        if status_data["properties"]["revision"][0:12] != req["revision"][0:12]:
            return COALESCED
        else:
            return SUCCESS

    def find_all_jobs_by_status(self, repo_name, revision, status):
        """
        Find all jobs with status 'status' in a given branch and revision.

        Returns a list with the request_ids of the jobs whose only status is 'status'.
        """
        all_jobs = self.get_all_jobs(repo_name, revision)
        request_id_by_buildername = {}
        right_status_buildernames = set()
        wrong_status_buildernames = set()
        for job in all_jobs:
            buildername = job["buildername"]
            try:
                if self.get_job_status(job) == status:
                    request_id = self.get_buildapi_request_id(repo_name, job)
                    request_id_by_buildername[buildername] = request_id
                    right_status_buildernames.add(buildername)
                else:
                    wrong_status_buildernames.add(buildername)
            except BuildjsonError:
                LOG.info('We were not able to find status information for "%s"'
                         % buildername)

        buildernames = right_status_buildernames - wrong_status_buildernames
        return sorted([request_id_by_buildername[b] for b in buildernames])


class TreeherderApi(QueryApi):

    def __init__(self):
        self.treeherder_client = TreeherderClient()

    def get_all_jobs(self, repo_name, revision, **params):
        """
        Return all jobs for a given revision.
        If we can't query about this revision in treeherder api, we return an empty list.
        """
        # We query treeherder for its internal revision_id, and then get the jobs from them.
        # We cannot get jobs directly from revision and repo_name in TH api.
        # See: https://bugzilla.mozilla.org/show_bug.cgi?id=1165401
        results = self.treeherder_client.get_resultsets(repo_name, revision=revision, **params)
        all_jobs = []
        if results:
            revision_id = results[0]["id"]
            all_jobs = self.treeherder_client.get_jobs(repo_name, count=2000,
                                                       result_set_id=revision_id, **params)
        return all_jobs

    def get_buildapi_request_id(self, repo_name, job):
        """ Method to return buildapi's request_id. """
        job_id = job["id"]
        query_params = {'job_id': job_id,
                        'name': 'buildapi'}
        LOG.debug("We are fetching request_id from treeherder artifacts api")
        artifact_content = self.treeherder_client.get_artifacts(repo_name,
                                                                **query_params)
        return artifact_content[0]["blob"]["request_id"]

    def get_hidden_jobs(self, repo_name, revision):
        """ Return all hidden jobs on Treeherder """
        return self.get_all_jobs(repo_name, revision=revision, visibility='excluded')

    def get_matching_jobs(self, repo_name, revision, buildername):
        """
        Return all jobs that matched the criteria.
        """
        LOG.debug("Find jobs matching '%s'" % buildername)
        all_jobs = self.get_all_jobs(repo_name, revision)
        matching_jobs = []
        for j in all_jobs:
            if j["ref_data_name"] == buildername:
                matching_jobs.append(j)

        LOG.debug("We have found %d job(s) of '%s'." %
                  (len(matching_jobs), buildername))
        return matching_jobs

    def get_job_status(self, job):
        """
        Helper to determine the scheduling status of a job from treeherder.

        Raises a TreeherderError if the job doesn't complete.
        """
        if job["job_coalesced_to_guid"] is not None:
            return COALESCED

        if job["result"] == "unknown":
            if job["state"] == "pending":
                return PENDING
            elif job["state"] == "running":
                return RUNNING
            else:
                return UNKNOWN

        # If the job 'state' is completed, we can have the following possible statuses:
        # https://github.com/mozilla/treeherder/blob/master/treeherder/etl/buildbot.py#L7
        status_dict = {
            "success": SUCCESS,
            "busted": FAILURE,
            "testfailed": FAILURE,
            "skipped": SKIPPED,
            "exception": EXCEPTION,
            "retry": RETRY,
            "usercancel": CANCELLED
            }

        if job["state"] == "completed":
            return status_dict[job["result"]]

        LOG.debug(job)
        raise TreeherderError("Unexpected status")

    def find_all_jobs_by_status(self, repo_name, revision, status):
        builder_names = []
        jobs = self.get_all_jobs(repo_name, revision)
        # filer out those jobs without builder name
        jobs = [job for job in jobs if job['machine_name'] != 'unknown']
        for job in jobs:
            try:
                job_status = self.get_job_status(job)
            except TreeherderError:
                continue
            if job_status == status:
                if job['build_system_type'] == 'taskcluster':
                    job_name = job['job_type_name']
                else:
                    job_name = job['ref_data_name']
                builder_names.append(job_name)
        return builder_names
