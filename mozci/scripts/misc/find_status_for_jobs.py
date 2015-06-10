import logging
import urllib

from argparse import ArgumentParser

from mozci.mozci import query_repo_name_from_buildername, _matching_jobs, \
    _status_info, _status_summary
from mozci.sources.buildapi import HOST_ROOT, RESULTS, COALESCED, \
    query_job_status, query_jobs_schedule

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-b', "--buildername",
                        dest="buildername",
                        required=True,
                        type=str,
                        help="The buildername used in Treeherder.")

    parser.add_argument("-r", "--revision",
                        dest="rev",
                        required=True,
                        help='The 12 character representing a revision (most recent).')

    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help="set debug for logging.")

    options = parser.parse_args()

    if options.debug:
        LOG.setLevel(logging.DEBUG)
        LOG.info("Setting DEBUG level")
    else:
        LOG.setLevel(logging.INFO)

    # requests is too noisy and adds no value
    logging.getLogger("requests").setLevel(logging.WARNING)

    repo_name = query_repo_name_from_buildername(options.buildername)
    all_jobs = query_jobs_schedule(repo_name, options.rev)
    jobs = _matching_jobs(options.buildername, all_jobs)
    import pprint
    for schedule_info in jobs:
        status = query_job_status(schedule_info)
        if status == COALESCED:
            print "%d %s %s/%s/build/%s" % \
                (schedule_info["requests"][0]["request_id"],
                 RESULTS[status], HOST_ROOT, repo_name, schedule_info["build_id"])
            status_info = _status_info(schedule_info)
            pprint.pprint(status_info)

            revision = status_info["properties"]["revision"]
            # Print the job that was coalesced with
            print 'https://treeherder.mozilla.org/#/jobs?%s%s' % \
                (urllib.urlencode({
                    'repo': repo_name,
                    'fromchange': schedule_info["revision"][0:12],
                    'tochange': revision[0:12],
                    'filter-searchStr': options.buildername}),
                    "&filter-resultStatus=success&filter-resultStatus=testfailed&filter-resultStatus=busted"
                    "&filter-resultStatus=exception&filter-resultStatus=retry&filter-resultStatus=usercancel"
                    "&filter-resultStatus=running&filter-resultStatus=pending&filter-resultStatus=coalesced")

    print "Status of all jobs (success, pending, running, coalesced)"
    print _status_summary(jobs)
