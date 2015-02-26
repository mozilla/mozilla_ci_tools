#! /usr/bin/env python
"""
This module is to extract information from
`allthething.json <https://secure.pub.build.mozilla.org/builddata/reports/allthethings.json>`_.
More info on how this data source is generated can be found in this
`wiki page <https://wiki.mozilla.org/ReleaseEngineering/How_To/allthethings.json>`_:

This module helps you extract data from allthethings.json
The data in that file is a dump of buildbot data structures.
It contains a dictionary with 4 keys:

* **builders**:

  * a dictionary in which keys are buildernames and values are the associated
    properties, for example:

::

    "Android 2.3 Armv6 Emulator mozilla-esr31 opt test crashtest-1": {
      "properties": {
        "branch": "mozilla-esr31",
        "platform": "android-armv6",
        "product": "mobile",
        "repo_path": "releases/mozilla-esr31",
        "script_repo_revision": "production",
        "slavebuilddir": "test",
        "stage_platform": "android-armv6"
      },
      "shortname": "mozilla-esr31_ubuntu64_vm_armv6_large_test-crashtest-1",
      "slavebuilddir": "test",
      "slavepool": "37085cdc35d8351f600c8c1cbd165c311880decb"
     },

* **schedulers**:

  * a dictionary mapping scheduler names to their downstream builders, for example:

::

    "Firefox mozilla-aurora linux l10n nightly": {
      "downstream": [
        "Firefox mozilla-aurora linux l10n nightly"
      ]
     },

* **master_builders**
* **slavepools**
"""
import json
import logging
import os
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
