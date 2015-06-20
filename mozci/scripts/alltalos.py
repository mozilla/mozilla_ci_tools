#! /usr/bin/env python

from argparse import ArgumentParser
import logging

from mozci.mozci import trigger_job
from mozci.platforms import build_talos_buildernames_for_repo, filter_buildernames

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()

PGO_ONLY_BRANCHES = ['mozilla-aurora', 'mozilla-beta']


def parse_args(argv=None):
    """Parse command line options."""
    parser = ArgumentParser()

    parser.add_argument("--repo-name",
                        dest="repo_name",
                        required=True,
                        help="The name of the repository: e.g. 'cedar'.")

    parser.add_argument("--times",
                        dest="times",
                        required=True,
                        type=int,
                        help="Number of times to retrigger the push.")

    parser.add_argument("--rev",
                        dest="revision",
                        help="revision of the push.")

    parser.add_argument("--dry-run",
                        action="store_true",
                        dest="dry_run",
                        help="flag to test without actual push.")

    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help="set debug for logging.")

    parser.add_argument("--pgo",
                        action="store_true",
                        dest="pgo",
                        help="trigger pgo tests (not non-pgo).")

    parser.add_argument("--trigger-build-if-missing",
                        action="store_true",
                        dest="trigger_build_if_missing",
                        help="trigger the build job even when there is no available. "
                        "This will only alter the behaviour on try")

    parser.add_argument("--includes",
                        action="store",
                        dest="includes",
                        help="comma-separated substring filter indicating which jobs to retrigger")

    parser.add_argument("--exclude",
                        action="store",
                        dest="exclude",
                        help="comma-separated substring filter indicating "
                             "which jobs not to retrigger")

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

    pgo = False
    if options.repo_name in PGO_ONLY_BRANCHES or options.pgo:
        pgo = True

    # on try we will change trigger_build_if_missing to False unless
    # the developer ran with --trigger-build-if-missing
    trigger_build_if_missing = True
    if not options.trigger_build_if_missing and options.repo_name == 'try':
        trigger_build_if_missing = False

    buildernames = build_talos_buildernames_for_repo(options.repo_name, pgo)

    # Filtering functionality
    filters_in, filters_out = [], []

    if options.includes:
        filters_in = options.includes.split(',')
    if options.exclude:
        filters_out = options.exclude.split(',')

    buildernames = filter_buildernames(filters_in, filters_out, buildernames)

    for buildername in buildernames:
        trigger_job(revision=options.revision,
                    buildername=buildername,
                    times=options.times,
                    dry_run=options.dry_run,
                    trigger_build_if_missing=trigger_build_if_missing)

if __name__ == '__main__':
    main()
