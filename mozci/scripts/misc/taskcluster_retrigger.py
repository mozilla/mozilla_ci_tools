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
    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help="set debug for logging.")

    parser.add_argument("--dry-run",
                        action="store_true",
                        dest="dry_run",
                        help="Dry run. No real actions are taken.")

    parser.add_argument('task_ids',
                        metavar='task_id',
                        type=str,
                        nargs='+',
                        help='Task IDs to work with.')

    options = parser.parse_args()

    if options.debug:
        LOG = setup_logging(logging.DEBUG)
    else:
        LOG = setup_logging()

    sch = TaskclusterSchedulingClient()
    for t_id in options.task_ids:
        ret_code = sch.retrigger(uuid=t_id, dry_run=options.dry_run)
        if ret_code < 0:
            LOG.warning("We could not retrigger task %s" % t_id)

if __name__ == "__main__":
    main()
