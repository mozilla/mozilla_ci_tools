'''
buildbot_to_taskcluster.py allows you to trigger a buildbot builder through
TaskCluster taking advantage of the Buildbot Bridge.
'''
import ast
import logging
import sys

from argparse import ArgumentParser

from mozci.ci_manager import TaskClusterBuildbotManager, TaskClusterManager
from mozci.platforms import get_downstream_jobs
from mozci.utils.log_util import setup_logging
from mozci.sources.buildbot_bridge import (
    trigger_builders_based_on_task_id,
    generate_tc_graph_from_builders
)
from mozci.sources.tc import credentials_available
from mozci.repositories import query_repo_url
from mozci.sources.pushlog import query_full_revision_info


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

    parser.add_argument("--children-of",
                        action="store",
                        dest="children_of",
                        type=str,
                        help="This allows you to request a list of all the associated "
                        "test jobs to a build job.")

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
        "Make sure you specify --repo-name and --revision"

    if not options.dry_run and not credentials_available():
        sys.exit(1)
    repo_url = query_repo_url(options.repo_name)
    revision = query_full_revision_info(repo_url,
                                        options.revision)
    builders = None
    if options.builders:
        builders = ast.literal_eval(options.builders)
    else:
        builders = get_downstream_jobs(options.children_of)

    if options.trigger_from_task_id and builders:
        trigger_builders_based_on_task_id(
            repo_name=options.repo_name,
            revision=revision,
            task_id=options.trigger_from_task_id,
            builders=builders,
            dry_run=options.dry_run
        )
    elif builders:
        tc_graph = generate_tc_graph_from_builders(
            builders=builders,
            repo_name=options.repo_name,
            revision=revision
        )
        mgr = TaskClusterManager()
        mgr.schedule_graph(
            task_graph=tc_graph,
            dry_run=options.dry_run
        )
    elif options.builders_graph:
        mgr = TaskClusterBuildbotManager()
        mgr.schedule_graph(
            repo_name=options.repo_name,
            revision=revision,
            builders_graph=ast.literal_eval(options.builders_graph),
            dry_run=options.dry_run
        )
    else:
        print "Please read the help menu to know what options are available to you."

if __name__ == "__main__":
    main()
