from argparse import ArgumentParser
import logging

from mozci.mozci import query_jobs_buildername

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()

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
