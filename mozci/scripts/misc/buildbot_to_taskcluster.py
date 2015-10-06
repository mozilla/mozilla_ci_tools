'''
buildbot_to_taskcluster.py allows you to trigger a buildbot builder through
TaskCluster taking advantage of the Buildbot Bridge.
'''
import ast
import logging

from argparse import ArgumentParser

from mozci.ci_manager import TaskClusterBuildbotManager
from mozci.utils.log_util import setup_logging
from mozci.sources.buildbot_bridge import trigger_builders_based_on_task_id


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

    parser.add_argument("--trigger-from-task-id",
                        action="store",
                        dest="trigger_from_task_id",
                        type=str,
                        help="Trigger builders based on build task (use with "
                        "--builders).")

    parser.add_argument("--builders",
                        action="store",
                        dest="builders",
                        type=str,
                        help="Use this if you want to pass a list of builders "
                        "(e.g. \"['builder 1']\".")

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

    assert options.repo_name and options.revision, \
        "Make sure you specify --repo-name and --revion"

    mgr = TaskClusterBuildbotManager()
    if options.trigger_from_task_id and options.builders:
        trigger_builders_based_on_task_id(
            repo_name=options.repo_name,
            revision=options.revision,
            task_id=options.trigger_from_task_id,
            builders=ast.literal_eval(options.builders),
            dry_run=options.dry_run
        )
    elif options.builders_graph:
        mgr.schedule_graph(
            repo_name=options.repo_name,
            revision=options.revision,
            builders_graph=ast.literal_eval(options.builders_graph),
            dry_run=options.dry_run
        )
    else:
        print "Please read the help menu to know what options are available to you."

if __name__ == "__main__":
    main()
