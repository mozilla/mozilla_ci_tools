'''
taskcluster_retrigger.py allows you to retrigger a task from TaskCluster
past its deadline.
'''
import logging

from argparse import ArgumentParser

from mozci.scheduling import TaskclusterSchedulingClient
from mozci.utils.misc import setup_logging


def main():
    parser = ArgumentParser()
    parser.add_argument('-r',
                        action="store_true",
                        dest="retrigger",
                        help="It retriggers a TaskCluster task.")

    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help="set debug for logging.")

    parser.add_argument('task_ids',
                        metavar='task_id',
                        type=str,
                        nargs='+',
                        help='Task IDs to work with.')

    options = parser.parse_args()

    if options.debug:
        setup_logging(logging.DEBUG)
    else:
        setup_logging()

    if options.retrigger:
        sch = TaskclusterSchedulingClient()
        for t_id in options.task_ids:
            sch.retrigger(uuid=t_id, dry_run=False)

if __name__ == "__main__":
    main()
