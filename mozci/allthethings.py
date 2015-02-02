#! /usr/bin/env python
"""
This module is to query allthethings.json
"""
import json
import logging
import os
import pprint

import requests

LOG = logging.getLogger()

ALLTHETHINGS = \
    "https://secure.pub.build.mozilla.org/builddata/reports/allthethings.json"


def _fetch_json(no_caching=False):
    file_name = 'allthethings.json'

    def _fetch():
        LOG.debug("Fetching allthethings.json %s" % ALLTHETHINGS)
        req = requests.get(ALLTHETHINGS)
        return req.json()

    if no_caching:
        data = _fetch()
    else:
        if os.path.exists(file_name):
            # XXX: We should remove the file if older than X minutes
            fd = open(file_name)
            data = json.load(fd)
        else:
            data = _fetch()
            with open(file_name, "wb") as fd:
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
