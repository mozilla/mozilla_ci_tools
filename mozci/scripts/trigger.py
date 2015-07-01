import logging
import urllib

from argparse import ArgumentParser

from mozci.mozci import find_backfill_revlist, trigger_range, set_query_source,\
    query_repo_name_from_buildername, query_repo_url_from_buildername, query_builders
from mozci.sources.buildapi import make_retrigger_request
from mozci.query_jobs import BuildApi, COALESCED
from mozci.sources.pushlog import query_revisions_range, \
    query_revisions_range_from_revision_before_and_after
from mozci.utils.misc import setup_logging
from mozci.sources.pushlog import query_repo_tip


def parse_args(argv=None):
    """Parse command line options."""
    parser = ArgumentParser()

    # Required arguments
    parser.add_argument('-b', "--buildername",
                        dest="buildernames",
                        type=str,
                        help="Comma-separated buildernames used in Treeherder.")

    parser.add_argument("-r", "--revision",
                        dest="rev",
                        required=True,
                        help='The 12 character representing a revision (most recent).')

    # Optional arguments
    parser.add_argument("--times",
                        dest="times",
                        type=int,
                        default=1,
                        help="Total number of jobs to have on a push. Eg: If there is\
                              1 job and you want to trigger 1 more time, do --times=2.")

    parser.add_argument("--skips",
                        dest="skips",
                        type=int,
                        help="Specify the step size to skip after every retrigger.")

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

    parser.add_argument("--query-source",
                        metavar="[buildapi|treeherder]",
                        dest="query_source",
                        default="buildapi",
                        help="Query info from buildapi or treeherder.")

    parser.add_argument("--file",
                        action="append",
                        dest="files",
                        help="Set files (typically an installer and test zip url "
                        "to be used in triggered jobs.")

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

    parser.add_argument("--coalesced",
                        action="store_true",
                        dest="coalesced",
                        help="Trigger every coalesced job on revision --rev "
                        "and repo --repo-name.")

    parser.add_argument("--repo-name",
                        dest="repo_name",
                        help="Branch name")

    options = parser.parse_args(argv)
    return options


def validate_options(options):
    error_message = ""
    if not options.buildernames and not options.coalesced:
        error_message = "A buildername is mandatory for all modes except --coalesced. " \
                        "Use --buildername."
    if options.coalesced and not options.repo_name:
        error_message = "A branch name is mandatory with --coalesced. Use --repo-name."

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


def sanitize_buildernames(buildernames):
    """Return the list of buildernames without trailing spaces and with the right capitalization."""
    buildernames_list = buildernames.split(',')
    repo_name = set(map(query_repo_name_from_buildername, buildernames_list))
    assert len(repo_name) == 1, "We only allow multiple buildernames on the same branch."
    ret_value = []
    for buildername in buildernames_list:
        buildername = buildername.strip()
        builders = query_builders()
        for builder in builders:
            if buildername.lower() == builder.lower():
                buildername = builder
        ret_value.append(buildername)
    return ret_value


def determine_revlist(repo_url, buildername, rev, back_revisions,
                      delta, from_rev, backfill, skips, max_revisions):
    """Determine which revisions we need to trigger."""
    if back_revisions:
        revlist = query_revisions_range_from_revision_before_and_after(
            repo_url=repo_url,
            revision=rev,
            before=back_revisions,
            after=0)

    elif delta:
        revlist = query_revisions_range_from_revision_before_and_after(
            repo_url=repo_url,
            revision=rev,
            before=delta,
            after=delta)

    elif from_rev:
        revlist = query_revisions_range(
            repo_url,
            to_revision=rev,
            from_revision=from_rev)

    elif backfill:
        revlist = find_backfill_revlist(
            repo_url=repo_url,
            revision=rev,
            max_revisions=max_revisions,
            buildername=buildername)

    else:
        revlist = [rev]

    if skips:
        revlist = revlist[::skips]

    return revlist


def main():
    options = parse_args()
    validate_options(options)

    if options.debug:
        LOG = setup_logging(logging.DEBUG)
        LOG.info("Setting DEBUG level")
    else:
        LOG = setup_logging(logging.INFO)

    # Setting the QUERY_SOURCE global variable in mozci.py
    set_query_source(options.query_source)

    if options.buildernames:
        options.buildernames = sanitize_buildernames(options.buildernames)
        repo_url = query_repo_url_from_buildername(options.buildernames[0])

    if not options.repo_name:
        options.repo_name = query_repo_name_from_buildername(options.buildernames[0])

    if options.rev == 'tip':
        options.rev = query_repo_tip(options.repo_name)
        LOG.info("The tip of %s is %s", options.repo_name, options.rev)

    if options.coalesced:
        query_api = BuildApi()
        request_ids = query_api.find_all_jobs_by_status(options.repo_name,
                                                        options.rev, COALESCED)
        if len(request_ids) == 0:
            LOG.info('We did not find any coalesced job')
        for request_id in request_ids:
            make_retrigger_request(repo_name=options.repo_name,
                                   request_id=request_id,
                                   dry_run=options.dry_run)

        return

    for buildername in options.buildernames:
        revlist = determine_revlist(
            repo_url=repo_url,
            buildername=buildername,
            rev=options.rev,
            back_revisions=options.back_revisions,
            delta=options.delta,
            from_rev=options.from_rev,
            backfill=options.backfill,
            skips=options.skips,
            max_revisions=options.max_revisions)

        try:
            trigger_range(
                buildername=buildername,
                revisions=revlist,
                times=options.times,
                dry_run=options.dry_run,
                files=options.files
            )
        except Exception, e:
            LOG.exception(e)
            exit(1)

        if revlist:
            LOG.info('https://treeherder.mozilla.org/#/jobs?%s' %
                     urllib.urlencode({'repo': options.repo_name,
                                       'fromchange': revlist[-1],
                                       'tochange': revlist[0],
                                       'filter-searchStr': buildername}))


if __name__ == "__main__":
    main()
