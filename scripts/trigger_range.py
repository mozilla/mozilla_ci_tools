import logging
import urllib

from argparse import ArgumentParser
from mozci.mozci import trigger_range, query_repo_url
from mozci.sources.pushlog import query_revisions_range_from_revision_and_delta
from mozci.sources.pushlog import query_revisions_range, query_revision_info, query_pushid_range

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()


def parse_args(argv=None):
    '''
    Parse command line options.
    '''
    parser = ArgumentParser()

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
                        help='The 12 character revision to start from (oldest).')

    parser.add_argument('--end-rev',
                        dest='end',
                        help='The 12 character revision to end with (newest).')

    parser.add_argument("--back-revisions",
                        dest="back_revisions",
                        type=int,
                        help="Number of revisions to go back from current revision (--rev).")

    parser.add_argument("--backfill",
                        action="store_true",
                        dest="backfill",
                        help="We will look in reverse chronological order until we find"
                        "the last revision where there was a good job.")

    parser.add_argument("--max-fill",
                        default=20,
                        dest="maxfill",
                        help="This is the maximum number of revisions we will fill in.")

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
    repo_url = query_repo_url_from_buildername(options.buildername)

    if (options.start or options.end) and \
       (options.delta or options.push_revision) and \
       (options.backfill or options.push_revision):
        raise Exception("Use either --start-rev and --end-rev together OR "
                        "use --rev and --delta together OR "
                        "use --rev and --backfill together.")

    if options.back_revisions and options.push_revision:
        push_info = query_revision_info(repo_url, options.push_revision)
        end_id = int(push_info["pushid"])
        start_id = end_id - options.back_revisions
        revlist = query_pushid_range(repo_url, start_id, end_id)

    if options.delta and options.push_revision:
        revlist = query_revisions_range_from_revision_and_delta(
            repo_url,
            options.push_revision,
            options.delta)

    if options.start and options.end:
        revlist = query_revisions_range(
            repo_url,
            options.start,
            options.end)

    if options.backfill and options.maxfill:
        push_info = query_revision_info(repo_url, options.push_revision)
        end_id = int(push_info["pushid"])
        start_id = end_id - options.maxfill
        revlist = query_pushid_range(repo_url, start_id, end_id)
        # XXX: We need to stop up to good job

    if options.debug:
        LOG.setLevel(logging.DEBUG)
        LOG.info("Setting DEBUG level")
    else:
        LOG.setLevel(logging.INFO)

    try:
        trigger_range(
            buildername=options.buildername,
            revisions=revlist,
            times=options.times,
            dry_run=options.dry_run
        )
    except Exception, e:
        LOG.exception(e)
        exit(1)

    LOG.info('https://treeherder.mozilla.org/#/jobs?%s' %
             urllib.urlencode({'repo': repo_name,
                               'fromchange': revlist[0],
                               'tochange': revlist[-1],
                               'filter-searchStr': options.buildername}))
