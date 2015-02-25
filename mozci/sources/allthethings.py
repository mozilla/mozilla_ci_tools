#! /usr/bin/env python
"""
This module helps you extract data from allthethings.json
The data in that file es a dump of buildbot data structures.
"""
import json
import logging
import os
import pprint
import time

import requests

LOG = logging.getLogger()

FILENAME = "allthethings.json"
ALLTHETHINGS = \
    "https://secure.pub.build.mozilla.org/builddata/reports/allthethings.json"


def fetch_allthethings_data(no_caching=False):
    '''
    It fetches the allthethings.json file.

    It clobbers it the file is older than 24 hours.

    If no_caching is True, we fetch it every time without creating a file.
    '''
    def _fetch():
        LOG.debug("Fetching allthethings.json %s" % ALLTHETHINGS)
        req = requests.get(ALLTHETHINGS)
        return req.json()

    if no_caching:
        data = _fetch()
    else:
        if os.path.exists(FILENAME):
            last_modified = int(os.path.getmtime(FILENAME))
            now = int(time.time())
            # If older than 24 hours, remove
            if (now - last_modified) > 24 * 60 * 60:
                os.remove(FILENAME)
                data = _fetch()
            else:
                fd = open(FILENAME)
                data = json.load(fd)
        else:
            data = _fetch()
            with open(FILENAME, "wb") as fd:
                json.dump(data, fd)
    return data


def list_builders():
    '''
    It returns a list of all builders running in the buildbot CI.
    '''
    j = fetch_allthethings_data()
    list = j["builders"].keys()
    assert list is not None, "The list of builders cannot be empty."
    return list


# Include this function in the documentation once we have proper
# documentation for it. Right now, this is not being used
def _query_job_info(name):
    ''' XXX: Determine what the data looks like
    '''
    j = fetch_allthethings_data()
    job_info = j["builders"][name]
    LOG.debug("Fetched information for %s:" % name)
    LOG.debug(pprint.pprint(job_info))
    return job_info
