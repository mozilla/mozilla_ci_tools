from argparse import ArgumentParser
import logging
import urllib

from mozci.mozci import backfill_revlist, trigger_range, \
    query_repo_name_from_buildername, query_repo_url_from_buildername
from mozci.sources.pushlog import query_revisions_range_from_revision_and_delta
from mozci.sources.pushlog import query_revisions_range, query_revision_info, query_pushid_range

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()


def parse_args(argv=None):
    """Parse command line options."""
    parser = ArgumentParser()

    # Required arguments
    parser.add_argument('-b', "--buildername",
                        dest="buildername",
                        required=True,
                        type=str,
                        help="The buildername used in Treeherder.")

    parser.add_argument("-r", "--revision",
                        dest="rev",
                        required=True,
                        help='The 12 character represneting a revision (most recent).')

    # Optional arguments
    parser.add_argument("--times",
                        dest="times",
                        type=int,
                        default=1,
                        help="Number of times to retrigger the push.")

    parser.add_argument('--from-rev',
                        dest='from_rev',
                        help='The 12 character representing the oldest push to start from.')

    parser.add_argument("--max-revisions",
                        dest="max_revisions",
                        default=20,
                        type=int,
                        help="This flag is used with --backfill. This flag limits"
                        "how many revisions we will look back until we find"
                        "the last revision where there was a good job.")

    parser.add_argument("--dry-run",
                        action="store_true",
                        dest="dry_run",
                        help="flag to test without actual push.")

    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help="set debug for logging.")

    # These are the various modes in which we can run this script
    parser.add_argument("--delta",
                        dest="delta",
                        type=int,
                        help="Number of jobs to add/subtract from push revision.")

    parser.add_argument("--back-revisions",
                        dest="back_revisions",
                        type=int,
                        help="Number of revisions to go back from current revision (--rev).")

    parser.add_argument("--backfill",
                        action="store_true",
                        dest="backfill",
                        help="We will trigger jobs starting from --rev in reverse chronological "
                        "order until we find the last revision where there was a good job.")

    options = parser.parse_args(argv)
    return options


def validate_options(options):
    error_message = ""
    if options.back_revisions:
        if options.backfill or options.delta or options.from_rev:
            error_message = "You should not pass --backfill, --delta or --end-rev " \
                            "when you use --back-revisions."

    elif options.backfill:
        if options.delta or options.from_rev:
            error_message = "You should not pass --delta or --end-rev " \
                            "when you use --backfill."
    elif options.delta:
        if options.from_rev:
            error_message = "You should not pass --end-rev " \
                            "when you use --delta."

    if error_message:
        raise Exception(error_message)


if __name__ == "__main__":
    options = parse_args()
    validate_options(options)

    if options.debug:
        LOG.setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)
        LOG.info("Setting DEBUG level")
    else:
        LOG.setLevel(logging.INFO)
        # requests is too noisy and adds no value
        logging.getLogger("requests").setLevel(logging.WARNING)

    repo_url = query_repo_url_from_buildername(options.buildername)

    if options.back_revisions:
        push_info = query_revision_info(repo_url, options.rev)
        end_id = int(push_info["pushid"])  # newest revision
        start_id = end_id - options.back_revisions
        revlist = query_pushid_range(repo_url=repo_url,
                                     start_id=start_id,
                                     end_id=end_id)

    elif options.delta:
        revlist = query_revisions_range_from_revision_and_delta(
            repo_url,
            options.rev,
            options.delta)

    elif options.from_rev:
        revlist = query_revisions_range(
            repo_url,
            to_revision=options.rev,
            from_revision=options.from_rev)

    elif options.backfill:
        push_info = query_revision_info(repo_url, options.rev)
        # A known bad revision
        end_id = int(push_info["pushid"])  # newest revision
        # The furthest we will go to find the last good job
        # We might find a good job before that
        start_id = end_id - options.max_revisions + 1
        revlist = query_pushid_range(repo_url=repo_url,
                                     start_id=start_id,
                                     end_id=end_id)

        revlist = backfill_revlist(
            options.buildername,
            revlist,
            options.times,
            options.dry_run
        )

    else:
        revlist = [options.rev]

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

    if revlist:
        LOG.info('https://treeherder.mozilla.org/#/jobs?%s' %
                 urllib.urlencode({'repo': query_repo_name_from_buildername(options.buildername),
                                   'fromchange': revlist[-1],
                                   'tochange': revlist[0],
                                   'filter-searchStr': options.buildername}))
