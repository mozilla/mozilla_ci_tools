'''
buildbot_to_taskcluster.py allows you to trigger a buildbot builder through
TaskCluster taking advantage of the Buildbot Bridge.
'''
import ast
import logging

from argparse import ArgumentParser

from mozci.ci_manager import TaskClusterBuildbotManager
from mozci.utils.misc import setup_logging


def main():
    parser = ArgumentParser()
    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help="set debug for logging.")

    parser.add_argument("--dry-run",
                        action="store_true",
                        dest="dry_run",
                        help="Dry run. No real actions are taken.")

    parser.add_argument("--repo-name",
                        action="store",
                        dest="repo_name",
                        type=str,
                        help="Repository name, e.g. mozilla-inbound.")

    parser.add_argument("--revision",
                        action="store",
                        dest="revision",
                        type=str,
                        help="12-char representing a push.")

    parser.add_argument("-b", "--builder",
                        action="store",
                        dest="builder",
                        type=str,
                        help="Use this if you just want to schedule one builder instead "
                        "of a graph.")

    parser.add_argument("-g", "--graph",
                        action="store",
                        dest="builders_graph",
                        help='Graph of builders in the form of: '
                             'dict(builder: [dep_builders].')

    options = parser.parse_args()

    if options.debug:
        setup_logging(logging.DEBUG)
    else:
        setup_logging()

    mgr = TaskClusterBuildbotManager()
    if options.builder:
        mgr.schedule_arbitrary_job(
            repo_name=options.repo_name,
            revision=options.revision,
            uuid=options.builder,
            dry_run=options.dry_run
        )
    else:
        mgr.schedule_graph(
            repo_name=options.repo_name,
            revision=options.revision,
            builders_graph=ast.literal_eval(options.builders_graph),
            dry_run=options.dry_run
        )

if __name__ == "__main__":
    main()
