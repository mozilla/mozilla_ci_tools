#! /usr/bin/env python
'''
This script helps us fill in missing jobs from a start revision to
an end revision.

We called it mozbisect instead of bisect because of a collision in urllib2.
'''

import argparse
import logging

from mozci.mozci import trigger_range

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
log = logging.getLogger()


def main():
    parser = argparse.ArgumentParser(
        usage='%(prog)s -b buildername --repo-name name '
        '--start-rev revision --end-rev revision [OPTION]...')
    parser.add_argument('-b', '--buildername', dest='buildername',
                        required=True,
                        help='The buildername used in Treeherder')
    parser.add_argument('--repo-name', dest='repo_name', required=True,
                        help="The name of the repository: e.g. 'cedar'")
    parser.add_argument('--start-rev', dest='start', required=True,
                        help='The 12 character revision to start from.')
    parser.add_argument('--end-rev', dest='end', required=True,
                        help='The 12 character revision to start from.')
    parser.add_argument('--num', dest='number', required=True,
                        help='Number of times that the job should be scheduled.')
    parser.add_argument('--debug', action='store_const', const=True,
                        help='Print debugging information')
    parser.add_argument('--dry-run', action='store_const', const=True,
                        help='Do not make post requests.')
    args = parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)
        log.info("Setting DEBUG level")

    trigger_range(
        buildername=args.buildername,
        repo_name=args.repo_name,
        start_revision=args.start,
        end_revision=args.end,
        times=args.number,
        dry_run=args.dry_run
    )

if __name__ == '__main__':
    main()
