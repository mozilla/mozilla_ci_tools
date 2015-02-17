import logging

from argparse import ArgumentParser
from mozci.mozci import trigger_range, query_repo_url
from mozci.sources.pushlog import query_revisions_range_from_revision_and_delta

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()


def parse_args(argv=None):
    '''
    Parse command line options.
    '''
    parser = ArgumentParser()
    parser.add_argument("--rev",
                        dest="push_revision",
                        required=True,
                        help="revision of the push.")

    parser.add_argument("--buildername",
                        dest="buildername",
                        required=True,
                        type=str,
                        help="buildername of the push.")

    parser.add_argument("--times",
                        dest="times",
                        required=True,
                        type=int,
                        help="number of times to retrigger the push.")

    parser.add_argument("--delta",
                        dest="delta",
                        required=True,
                        type=int,
                        help="number of jobs to add/subtract from push revision.")

    parser.add_argument("--repo_name",
                        dest="repo_name",
                        required=True,
                        help="The name of the repository: e.g. 'cedar'.")

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
    revlist = query_revisions_range_from_revision_and_delta(
                repo_url,
                options.push_revision,
                options.repo_name,
                options.delta
                )
    start_rev = revlist[0]
    end_rev = revlist[-1]

    if options.debug:
        LOG.setLevel(logging.DEBUG)

    try:
        trigger_range(
            buildername=options.buildername,
            repo_name=options.repo_name,
            start_revision=start_rev,
            end_revision=end_rev,
            times=options.times,
            dry_run=options.dry_run
        )
    except:
        raise Exception("Error running trigger_range")

    LOG.info('https://treeherder.mozilla.org/#/jobs?repo=mozilla-inbound&fromchange=%s'
             '&tochange=%s&filter-searchStr=%s' % (start_rev, end_rev, options.buildername))
