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
        r = requests.get(ALLTHETHINGS)
        return r.json()

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
    return j["builders"].keys()


def valid_builder(repo_name, buildername):
    ''' This function determines if the builder you're trying to trigger is
    valid.
    '''
    j = _fetch_json()
    if buildername in j["builders"]:
        LOG.debug("Buildername %s is valid." % buildername)
        return True
    else:
        LOG.warning("Buildername %s is *NOT* valid." % buildername)
        LOG.info("Check the file we just created builders.txt for "
                 "a list of valid builders.")
        builders = list_builders()
        with open("builders.txt", "wb") as fd:
            for b in sorted(builders):
                fd.write(b + "\n")

        return False


def query_job_info(name):
    j = _fetch_json()
    job_info = j["builders"][name]
    LOG.debug("Fetched information for %s:" % name)
    LOG.debug(pprint.pprint(job_info))
    return job_info
