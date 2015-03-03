#! /usr/bin/env python

from argparse import ArgumentParser
import logging
import re

from mozci.mozci import trigger_job, query_builders

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
log = logging.getLogger()

PGO_ONLY_BRANCHES = ['mozilla-aurora', 'mozilla-beta']


def talos_buildernames(repo_name, pgo_only=False):
    """
        This function aims to generate all possible talos jobs for a given branch.
        #TODO: what if jobs change (new jobs/platforms that come with an uplift or get removed)?
        #TODO: somehow mozilla beta/aurora has non-pgo buildernames when we only do pgo
    """
    builders = query_builders()
    buildernames = []

    pgo_re = re.compile(".*%s pgo talos.*" % repo_name)
    osx_re = re.compile(".*OSX.*%s talos.*" % repo_name)
    android_re = re.compile(".*Android.* %s talos.*" % repo_name)
    talos_re = re.compile(".*%s talos.*" % repo_name)

    regex_list = [talos_re]
    if repo_name in PGO_ONLY_BRANCHES or pgo_only:
        regex_list = [pgo_re, osx_re, android_re]

    for builder in builders:
        for regex in regex_list:
            if regex.match(builder):
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

    options = parser.parse_args(argv)
    return options


def main():
    options = parse_args()

    if options.debug:
        log.setLevel(logging.DEBUG)
        log.info("Setting DEBUG level")

    buildernames = talos_buildernames(options.repo_name)

    for buildername in buildernames:
        trigger_job(repo_name=options.repo_name,
                    revision=options.revision,
                    buildername=buildername,
                    times=options.times,
                    dry_run=options.dry_run)

if __name__ == '__main__':
    main()
