from argparse import ArgumentParser
import logging

from mozci.query_jobs import BuildApi
from mozci.mozci import query_repo_name_from_buildername, _status_info

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()


def query_jobs_buildername(buildername, revision):
    """Return **status** information for a buildername on a given revision."""
    # NOTE: It's unfortunate that there is scheduling and status data.
    #       I think we might need to remove this distinction for the user's
    #       sake.
    status_info = []
    repo_name = query_repo_name_from_buildername(buildername)
    query_api = BuildApi()
    jobs = query_api.get_matching_jobs(repo_name, revision, buildername)
    # The user wants the status data rather than the scheduling data
    for job_schedule_info in jobs:
        status_info.append(_status_info(job_schedule_info))

    return status_info


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-b', "--buildername",
                        dest="buildername",
                        required=True,
                        type=str,
                        help="The buildername used in Treeherder.")

    parser.add_argument("-r", "--revision",
                        dest="rev",
                        required=True,
                        help='The 12 character representing a revision (most recent).')

    options = parser.parse_args()

    jobs = query_jobs_buildername(options.buildername, options.rev)
    for schedule_info in jobs:
        print schedule_info["properties"]["log_url"]
