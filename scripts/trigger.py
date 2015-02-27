#! /usr/bin/env python
# This script is designed to trigger an arbitrary job
# http://johnzeller.com/blog/2014/03/12/triggering-of-arbitrary-buildstests-is-now-possible
'''
usage: trigger.py -b buildername --rev revision [OPTION]...

optional arguments:
  -h, --help            show this help message and exit
  -b BUILDERNAME, --buildername BUILDERNAME
                        The buildername used in Treeherder
  --rev REVISION        The 12 character revision.
  --file FILES          Append files needed to run the job (e.g.installer,
                        test.zip)
  --debug               Print debugging information
  --dry-run             Do not make post requests.
'''

import argparse
import logging

from mozci.mozci import trigger_job, query_jobs_schedule_url, query_repo_name_from_buildername

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()
LOG.setLevel(logging.INFO)


def main():
    parser = argparse.ArgumentParser(
        usage='%(prog)s -b buildername --rev revision [OPTION]...')
    parser.add_argument('-b', '--buildername', dest='buildername',
                        required=True,
                        help='The buildername used in Treeherder')
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
    repo_name = query_repo_name_from_buildername(args.buildername)

    if args.debug:
        LOG.setLevel(logging.DEBUG)
        LOG.info("Setting DEBUG level")

    list_of_requests = trigger_job(
        repo_name=repo_name,
        revision=args.revision,
        buildername=args.buildername,
        files=args.files,
        dry_run=args.dry_run
    )

    for req in list_of_requests:
        if req is not None:
            if req.status_code == 202:
                LOG.info("You return code is: %s" % req.status_code)
                LOG.info("See your running jobs in here:")
                LOG.info(query_jobs_schedule_url(repo_name, args.revision))
            else:
                LOG.error("Something has gone wrong. We received "
                          "status code: %s" % req.status_code)

if __name__ == '__main__':
    main()
