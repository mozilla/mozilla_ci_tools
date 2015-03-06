#! /usr/bin/env python

from argparse import ArgumentParser
import logging
import re

from mozci.mozci import trigger_job, query_builders

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()

PGO_ONLY_BRANCHES = ['mozilla-aurora', 'mozilla-beta']


def talos_buildernames(repo_name, pgo_only=False):
    """
        This function aims to generate all possible talos jobs for a given branch.
        #TODO: somehow mozilla beta/aurora has non-pgo buildernames when we only do pgo
    """
    builders = query_builders()
    buildernames = []

    # Android and OSX do not have PGO, so we need to get those specific jobs
    pgo_re = re.compile(".*%s pgo talos.*" % repo_name)
    talos_re = re.compile(".*%s talos.*" % repo_name)

    talos_jobs = set()
    pgo_jobs = set()
    tp_jobs = set()
    for builder in builders:
        if talos_re.match(builder):
            talos_jobs.add(builder)

        if pgo_re.match(builder):
            pgo_jobs.add(builder)
            tp_jobs.add(builder.replace(' pgo', ''))

    if repo_name in PGO_ONLY_BRANCHES or pgo_only:
        non_pgo_jobs = talos_jobs - tp_jobs
        talos_jobs = pgo_jobs.union(non_pgo_jobs)

    buildernames = []
    for builder in talos_jobs:
        buildernames.append(builder)

    buildernames.sort()
    return buildernames


def parse_args(argv=None):
    '''
    Parse command line options.
    '''
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

    options = parser.parse_args(argv)
    return options


def main():
    options = parse_args()

    if options.debug:
        LOG.setLevel(logging.DEBUG)
        LOG.info("Setting DEBUG level")

    buildernames = talos_buildernames(options.repo_name, options.pgo)

    for buildername in buildernames:
        trigger_job(revision=options.revision,
                    buildername=buildername,
                    times=options.times,
                    dry_run=options.dry_run)

if __name__ == '__main__':
    main()
