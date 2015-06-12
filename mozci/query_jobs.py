import logging
import requests

from abc import ABCMeta, abstractmethod
from thclient import TreeherderClient
from sources import buildapi
from sources.buildjson import query_job_data, BuildjsonException
from utils.authentication import get_credentials


LOG = logging.getLogger('mozci')
PENDING, RUNNING, COALESCED, UNKNOWN = range(-4, 0)
SUCCESS, WARNING, FAILURE, SKIPPED, EXCEPTION, RETRY, CANCELLED = range(7)
JOBS_CACHE = {}


class TreeherderException(Exception):
    pass


class QueryApi(object):
    """ Base class for common query methods """

    __metaclass__ = ABCMeta

    def __init__(self, query_source):
        self.query_source = query_source

    @abstractmethod
    def get_all_jobs(self, repo_name, revision):
        pass

    @abstractmethod
    def get_matching_jobs(self, buildername, all_jobs):
        pass

    @abstractmethod
    def get_buildapi_request_id(self, repo_name, job):
        pass

    @abstractmethod
    def get_job_status(self, job):
        pass


class BuildApi(QueryApi):

    def __init__(self):
        super(BuildApi, self).__init__("buildapi")

    def get_all_jobs(self, repo_name, revision):
        """
        Return a list with all jobs for that revision.

        If we can't query about this revision in buildapi we return an empty list.

        raises BuildapiException
        """
        if (repo_name, revision) in JOBS_CACHE:
            return JOBS_CACHE[(repo_name, revision)]

        JOBS_CACHE[(repo_name, revision)] = \
                                        buildapi.query_for_jobs(repo_name, revision)
        return JOBS_CACHE[(repo_name, revision)]

    def get_buildapi_request_id(self, repo_name, job):
        """ Method to return buildapi's request_id for a job. """
        return job["requests"][0]["request_id"]

    def get_matching_jobs(self, buildername, all_jobs):
        """Return all jobs that matched the criteria."""
        LOG.debug("Find jobs matching '%s'" % buildername)
        matching_jobs = []
        for j in all_jobs:
            if j["buildername"] == buildername:
                matching_jobs.append(j)

        LOG.debug("We have found %d job(s) of '%s'." %
                  (len(matching_jobs), buildername))
        return matching_jobs

    def get_job_status(self, job):
        """Helper to determine the scheduling status of a job from self-serve."""
        if not ("status" in job):
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
            if self._is_coalesced(job):
                return COALESCED
            return SUCCESS

        LOG.debug(job)
        raise buildapi.BuildapiException("Unexpected status")

    def _is_coalesced(self, job):
        """Helper method to determine if a job with status 'SUCCESS' is coalesced."""
        assert job["status"] == SUCCESS

        req = job["requests"][0]
        status_data = query_job_data(req["complete_at"], req["request_id"])
        return status_data["properties"]["revision"][0:12] != req["revision"][0:12]

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
            except buildjson.BuildjsonException:
                LOG.info('We were not able to find status information for "%s"'
                         % buildername)

        buildernames = right_status_buildernames - wrong_status_buildernames
        return sorted([request_id_by_buildername[b] for b in buildernames])


class TreeherderApi(QueryApi):

    def __init__(self):
        super(TreeherderApi, self).__init__("treeherder")
        self.treeherder_client = TreeherderClient()

    def get_all_jobs(self, repo_name, revision):
        """
        Return all jobs for a given revision.
        If we can't query about this revision in treeherder api, we return an empty list.
        """
        results = self.treeherder_client.get_resultsets(repo_name, revision=revision)
        all_jobs = []
        if results:
            revision_id = results[0]["id"]
            all_jobs = self.treeherder_client.get_jobs(repo_name, count=2000,
                                                  result_set_id=revision_id)
        return all_jobs

    def get_buildapi_request_id(self, repo_name, job):
        """ Method to return buildapi's request_id. """
        job_id = job["id"]
        query_params = {'job_id': job_id,
                        'name': 'buildapi'}
        LOG.debug("We are fetching request_id from treeherder artifacts api")
        artifact_content = self.treeherder_client.get_artifacts(repo_name,
                                                                query_params)
        return artifact_content[0]["blob"]["request_id"]

    def get_matching_jobs(self, buildername, all_jobs):
        """
        Return all jobs that matched the criteria.
        """
        LOG.debug("Find jobs matching '%s'" % buildername)
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
        """
        if job["result"] == "unknown":
            if job["state"] == "pending":
                return PENDING
            elif job["state"] == "running":
                return RUNNING
            else:
                return UNKNOWN

        if job["job_coalesced_to_guid"] is not None:
            return COALESCED

        if job["state"] == "completed":
            if job["result"] == "success":
                return SUCCESS
            elif job["result"] == "busted" or job["result"] == "testfailed":
                return FAILURE
            elif job["result"] == "skipped":
                return SKIPPED
            elif job["result"] == "exception":
                return EXCEPTION
            elif job["result"] == "retry":
                return RETRY
            elif job["result"] == "usercancel":
                return CANCELLED

        LOG.debug(job)
        raise TreeherderException("Unexpected status")
