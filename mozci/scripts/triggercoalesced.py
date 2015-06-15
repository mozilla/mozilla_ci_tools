"""
This script retriggers every coalesced job on a revision/branch.

usage:
python triggercoalesced.py repo rev
"""
import logging

from argparse import ArgumentParser

from mozci.sources.buildapi import find_all_coalesced, make_retrigger_request

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()


def parse_args(argv=None):
    """Parse command line options."""
    parser = ArgumentParser()

    # Required arguments

    parser.add_argument("repo",
                        help='Branch name')

    parser.add_argument("rev",
                        help='The 12 characters representing a revision.')

    # Optional arguments
    parser.add_argument("--dry-run",
                        action="store_true",
                        dest="dry_run",
                        help="flag to test without actual push.")

    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help="set debug for logging.")

    options = parser.parse_args(argv)
    return options


def main():
    options = parse_args()

    if options.debug:
        LOG.setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)
        LOG.info("Setting DEBUG level")
    else:
        LOG.setLevel(logging.INFO)
        # requests is too noisy and adds no value
        logging.getLogger("requests").setLevel(logging.WARNING)

    requests = find_all_coalesced(options.repo, options.rev)

    for request in requests:
        make_retrigger_request(repo_name=options.repo,
                               request_id=request,
                               dry_run=options.dry_run)

if __name__ == '__main__':
    main()
