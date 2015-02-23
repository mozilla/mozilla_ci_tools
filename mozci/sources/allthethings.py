#! /usr/bin/env python
"""
This module is to query allthethings.json
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


def _fetch_json(no_caching=False):
    ''' Fetch allthethings.json file.

    Clobber it if older than 24 hours.

    If no_caching is True, fetch it every time without creating a file.
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
    ''' Returns list of all builders.
    '''
    j = _fetch_json()
    list = j["builders"].keys()
    assert list is not None, "The list of builders cannot be empty."
    return list


def query_job_info(name):
    ''' XXX: Determine what the data looks like
    '''
    j = _fetch_json()
    job_info = j["builders"][name]
    LOG.debug("Fetched information for %s:" % name)
    LOG.debug(pprint.pprint(job_info))
    return job_info
