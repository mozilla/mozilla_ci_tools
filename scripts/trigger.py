#! /usr/bin/env python
# This script is designed to trigger an arbitrary job
# http://johnzeller.com/blog/2014/03/12/triggering-of-arbitrary-buildstests-is-now-possible

import argparse
import logging

from mozci.buildapi import trigger_job, jobs_running_url
from mozci.utils.authentication import get_credentials

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
log = logging.getLogger()


def main():
    parser = argparse.ArgumentParser(
        usage='%(prog)s -b buildername --repo-name name '
        '--rev revision [OPTION]...')
    parser.add_argument('-b', '--buildername', dest='buildername',
                        required=True,
                        help='The buildername used in Treeherder')
    parser.add_argument('--repo-name', dest='repo_name', required=True,
                        help="The name of the repository: e.g. 'cedar'")
    parser.add_argument('--rev', dest='revision', required=True,
                        help='The 12 character revision.')
    parser.add_argument('--file', dest='files', action="append", default=[],
                        help='Append files needed to run the job (e.g.'
                        'installer, test.zip)')
    parser.add_argument('--debug', action='store_const', const=True,
                        help='Print debugging information')
    parser.add_argument('--dry-run', action='store_const', const=True,
                        help='Do not make post requests.')
    args = parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)
        log.info("Setting DEBUG level")

    auth = get_credentials()

    r = trigger_job(
        repo_name=args.repo_name,
        revision=args.revision,
        buildername=args.buildername,
        auth=auth,
        files=args.files,
        dry_run=args.dry_run
    )

    if r is not None:
        if r.status_code == 202:
            log.info("You return code is: %s" % r.status_code)
            log.info("See your running jobs in here:")
            log.info(jobs_running_url(args.repo_name, args.revision))
        else:
            log.error("Something has gone wrong. We received "
                      "status code: %s" % r.status_code)

if __name__ == '__main__':
    main()
