import json
import logging
import os
import shutil
import time

from tempfile import NamedTemporaryFile

import requests

LOG = logging.getLogger()


def path_to_file(filename):
    """Add files to .mozilla/mozci"""
    path = os.path.expanduser('~/.mozilla/mozci/')
    if not os.path.exists(path):
        os.makedirs(path)
    filepath = os.path.join(path, filename)
    return filepath


def _save_json_file(req, filename):
    # NOTE: requests deals with decompressing the gzip file
    """
    Helper private function to simply save a file and to verify that is valid json.
    """
    if not os.path.isabs(filename):
        filename = path_to_file(filename)

    LOG.debug("About to fetch %s from %s" % (filename, req.url))

    blob = ""
    for chunk in req.iter_content(chunk_size=1024):
        if chunk:  # filter out keep-alive new chunks
            blob += chunk

    try:
        # This will raise an JsonDecoderException if it is not valid json
        json_content = json.loads(blob)
    except ValueError:
        LOG.error("The obtained json from %s came corrupted. We're not "
                  "writing to disk." % req.url)
        exit(1)

    temp_file = NamedTemporaryFile(delete=False)
    with open(temp_file.name, 'wb') as fd:
        json.dump(json_content, fd)

    LOG.debug("Moving %s to %s" % (temp_file.name, filename))
    shutil.move(temp_file.name, filename)


def fetch_file(filename, url):
    """
    We download a file and use streaming to improve the chances of success.

    We also check if the file on the server is newer or not to determine if we should download it.
    """
    if not os.path.isabs(filename):
        filename = path_to_file(filename)

    if os.path.exists(filename):
        statinfo = os.stat(filename)
        last_mod_date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(statinfo.st_mtime))

        req = requests.get(url, headers={'If-Modified-Since': last_mod_date}, stream=True)

        if req.status_code == 200:
            LOG.debug("The local file was last modified in %s. We need to delete the file and fetch it again." % last_mod_date)
            os.remove(filename)
            _save_json_file(req, filename)
        elif req.status_code == 304:
            LOG.debug("%s is on disk and was last modified on %s" % (filename, last_mod_date))
        else:
            raise Exception("We received %s which is unexpected." % req.status_code)
    else:
        LOG.debug("We have not been able to find on disk %s." % filename)
        req = requests.get(url, stream=True)
        _save_json_file(req, filename)
