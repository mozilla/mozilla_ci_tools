import logging

from argparse import ArgumentParser
from mozci.mozci import trigger_range, query_repo_url
from mozci.sources.pushlog import query_revisions_range_from_revision_and_delta
from mozci.sources.pushlog import query_revisions_range

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()


def parse_args(argv=None):
    '''
    Parse command line options.
    '''
    parser = ArgumentParser()

    parser.add_argument("--repo-name",
                        dest="repo_name",
                        required=True,
                        help="The name of the repository: e.g. 'cedar'.")

    parser.add_argument('-b', "--buildername",
                        dest="buildername",
                        required=True,
                        type=str,
                        help="The buildername used in Treeherder.")

    parser.add_argument("--times",
                        dest="times",
                        required=True,
                        type=int,
                        help="Number of times to retrigger the push.")

    parser.add_argument("--delta",
                        dest="delta",
                        type=int,
                        help="Number of jobs to add/subtract from push revision.")

    parser.add_argument("--rev",
                        dest="push_revision",
                        help="revision of the push.")

    parser.add_argument('--start-rev',
                        dest='start',
                        help='The 12 character revision to start from.')

    parser.add_argument('--end-rev',
                        dest='end',
                        help='The 12 character revision to start from.')

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


if __name__ == "__main__":
    options = parse_args()
    repo_url = query_repo_url(options.repo_name)

    if (options.start or options.end) and (options.delta or options.push_revision):
        raise Exception("Use either --start-rev and --end-rev together OR"
                        " use --rev and --delta together.")

    if options.delta and options.push_revision:
        revlist = query_revisions_range_from_revision_and_delta(
                    repo_url,
                    options.push_revision,
                    options.repo_name,
                    options.delta)

    if options.start and options.end:
        revlist = query_revisions_range(
                    repo_url,
                    options.start,
                    options.end)

    if options.debug:
        LOG.setLevel(logging.DEBUG)
        LOG.info("Setting DEBUG level")
    try:
        trigger_range(
            buildername=options.buildername,
            repo_name=options.repo_name,
            revisions=revlist,
            times=options.times,
            dry_run=options.dry_run
        )
    except:
        raise Exception("Error running trigger_range")

    LOG.info('https://treeherder.mozilla.org/#/jobs?repo=mozilla-inbound&fromchange=%s'
             '&tochange=%s&filter-searchStr=%s' % (revlist[0], revlist[-1], options.buildername))
