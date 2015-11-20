"""
This script retriggers N times every job that matches --includes and doesn't match --exclude .
usage:
python th_filters.py repo rev --includes "args to include" --exclude  "args to exclude --times N"
"""
import logging
import urllib
import sys

from argparse import ArgumentParser

from mozci.mozci import (
    query_repo_name_from_buildername,
    query_builders, set_query_source,
    trigger_range
)
from mozci.platforms import filter_buildernames
from mozci.utils.log_util import setup_logging
from mozci.utils.authentication import valid_credentials
from mozci.sources.buildapi import query_repo_url
from mozci.sources.pushlog import (
    query_repo_tip,
    query_full_revision_info
)


def parse_args(argv=None):
    """Parse command line options."""
    parser = ArgumentParser()

    # Required arguments

    parser.add_argument("repo",
                        help='Branch name')

    parser.add_argument("rev",
                        help='The 12 character representing a revision (most recent).')

    parser.add_argument('-i', "--includes",
                        dest="includes",
                        required=True,
                        type=str,
                        help="comma-separated treeherder filters to include.")

    parser.add_argument('-e', "--exclude",
                        dest="exclude",
                        type=str,
                        help="comma-separated treeherder filters to exclude.")

    parser.add_argument("--times",
                        dest="times",
                        type=int,
                        default=1,
                        help="Total number of jobs to have on a push. Eg: If there is\
                              1 job and you want to trigger 1 more time, do --times=2.")

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

    parser.add_argument("--existing-only",
                        action="store_false",
                        dest="existing_only",
                        help="Only trigger test jobs if the build jobs already exists.")

    options = parser.parse_args(argv)
    return options


def main():
    options = parse_args()
    repo_url = query_repo_url(options.repo)
    if not valid_credentials():
        sys.exit(-1)

    if options.debug:
        LOG = setup_logging(logging.DEBUG)
    else:
        LOG = setup_logging(logging.INFO)

    if options.rev == 'tip':
        revision = query_repo_tip(repo_url)
        LOG.info("The tip of %s is %s", options.repo, revision)

    else:
        revision = query_full_revision_info(repo_url, options.rev)
    filters_in = options.includes.split(',') + [options.repo]
    filters_out = []

    if options.exclude:
        filters_out = options.exclude.split(',')

    buildernames = filter_buildernames(
        buildernames=query_builders(repo_name=options.repo),
        include=filters_in,
        exclude=filters_out
    )

    if len(buildernames) == 0:
        LOG.info("0 jobs match these filters, please try again.")
        return

    if options.existing_only:
        cont = raw_input("The ones which have existing builds out of %i jobs will be triggered,\
                         do you wish to continue? y/n/d (d=show details) " % len(buildernames))
    else:
        cont = raw_input("%i jobs will be triggered, do you wish to continue? \
                          y/n/d (d=show details) " % len(buildernames))

    if cont.lower() == 'd':
        LOG.info("The following jobs will be triggered: \n %s" % '\n'.join(buildernames))
        cont = raw_input("Do you wish to continue? y/n ")

    if cont.lower() != 'y':
        exit(1)

    # Setting the QUERY_SOURCE global variable in mozci.py
    set_query_source(options.query_source)
    for buildername in buildernames:
        repo_name = query_repo_name_from_buildername(buildername)

        trigger_build_if_missing = True
        if options.existing_only or repo_name == 'try':
            trigger_build_if_missing = False

        trigger_range(
            buildername=buildername,
            revisions=[revision],
            times=options.times,
            dry_run=options.dry_run,
            trigger_build_if_missing=trigger_build_if_missing,
        )

    LOG.info('https://treeherder.mozilla.org/#/jobs?%s' %
             urllib.urlencode({'repo': options.repo,
                               'revision': revision}))

if __name__ == '__main__':
    main()
