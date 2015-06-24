import calendar
import datetime
import errno
import fnmatch
import gzip
import json
import logging
import os
import platform
import shutil
import subprocess
import time

import requests

from progressbar import Bar, Timer, FileTransferSpeed, ProgressBar

# yajl2 backend is faster then the default backend, but it requires
# libyajl2 to be installed in the system
try:
    import ijson.backends.yajl2 as ijson
except:
    import ijson

LOG = logging.getLogger('mozci')
MEMORY_SAVING_MODE = False


def path_to_file(filename):
    """Add files to .mozilla/mozci"""
    path = os.path.expanduser('~/.mozilla/mozci/')
    if not os.path.exists(path):
        os.makedirs(path)
    filepath = os.path.join(path, filename)
    return filepath


def clean_directory():
    """Clean ./mozilla/mozci directory of buildjson files that are older than 30 days"""
    path = os.path.expanduser('~/.mozilla/mozci/')
    filter_build_files = fnmatch.filter(os.listdir(path), "builds-*")
    permissible_last_date = datetime.date.today() - datetime.timedelta(days=30)
    permissible_timestamp = int(permissible_last_date.strftime("%s"))
    for filename in filter_build_files:
        full_filepath = os.path.join(path, filename)
        last_mod_timestamp = int(os.stat(full_filepath).st_mtime)
        if last_mod_timestamp < permissible_timestamp:
            LOG.info("Cleaning up %s" % full_filepath)
            os.remove(full_filepath)


def _verify_last_mod(remote_last_mod_date, filename):
    # Create a struct_time based on the server's last modified
    datetime_struct = time.strptime(remote_last_mod_date, "%a, %d %b %Y %H:%M:%S %Z")
    # Convert the struct_time to a local timestamp (instead of GMT timezone)
    local_timestamp = calendar.timegm(datetime_struct)
    # Set the creation and modified of the file
    os.utime(filename, (local_timestamp, local_timestamp))
    statinfo = os.stat(filename)
    last_mod_date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(statinfo.st_mtime))

    assert remote_last_mod_date == last_mod_date, \
        "The modified time of the file (%s) should match the one of the server (%s)." % \
        (last_mod_date, remote_last_mod_date)


class DownloadProgressBar(ProgressBar):
    '''
    Helper class to show download progress.
    '''
    def __init__(self, filename, size):
        widgets = [
            os.path.basename(filename), ": ",
            Bar(marker=">", left="[", right="]"), ' ',
            Timer(), ' ',
            FileTransferSpeed(), " ",
            "{0}MB".format(round(size / 1024 / 1024, 2))
        ]
        super(DownloadProgressBar, self).__init__(widgets=widgets, maxval=size)


def _load_json_file(filepath):
    '''
    This is a helper function to load json contents from a file
    '''
    LOG.debug("About to load %s." % filepath)

    # Sniff whether the file is gzipped
    fd = open(filepath, 'r')
    magic = fd.read(2)
    fd.seek(0)

    if magic == '\037\213':  # gzip magic number
        if platform.system() == 'Windows':
            # Windows doesn't like multiple processes opening the same files
            fd.close()
            # Issue 202 - gzip.py on Windows does not handle big files well
            cmd = ["gzip", "-cd", filepath]
            LOG.debug("-> %s" % ' '.join(cmd))
            try:
                data = subprocess.check_output(cmd)
            except subprocess.CalledProcessError, e:
                if e.errno == errno.ENOENT:
                    raise Exception(
                        "You don't have gzip installed on your system. "
                        "Please install it. You can find it inside of mozilla-build."
                    )
        else:
            gzipper = gzip.GzipFile(fileobj=fd)
            data = gzipper.read()
            gzipper.close()

    else:
        data = fd.read()

    if platform.system() != 'Windows':
        fd.close()

    try:
        return json.loads(data)
    except ValueError, e:
        LOG.exception(e)
        new_file = filepath + ".corrupted"
        shutil.move(filepath, new_file)
        LOG.error("The file on-disk does not have valid data")
        LOG.info("We have moved %s to %s for inspection." % (filepath, new_file))
        exit(1)


def _save_file(req, filepath):
    '''
    Helper class to download a file and show a progress bar.
    '''
    LOG.debug("About to fetch %s from %s" % (filepath, req.url))
    size = int(req.headers['Content-Length'].strip())
    pbar = DownloadProgressBar(filepath, size).start()
    bytes = 0
    with open(filepath, 'w') as fd:
        for chunk in req.iter_content(10 * 1024):
            if chunk:  # filter out keep-alive new chunks
                fd.write(chunk)
                bytes += len(chunk)
                pbar.update(bytes)
    pbar.finish()
    _verify_last_mod(req.headers['last-modified'], filepath)


def load_file(filename, url):
    '''
    We download a file without decompressing it so we can keep track of its progress.
    We save it to disk and return the contents of it.
    We also check if the file on the server is newer to determine if we should download it again.

    raises Exception if anything goes wrong.
    '''
    # Obtain the absolute path to our file in the cache
    if not os.path.isabs(filename):
        filepath = path_to_file(filename)
    else:
        filepath = filename

    headers = {
        'Accept-Encoding': None,
    }

    exists = os.path.exists(filepath)

    if exists:
        # The file exists in the cache, let's verify that is still current
        statinfo = os.stat(filepath)
        last_mod_date = time.strftime('%a, %d %b %Y %H:%M:%S GMT',
                                      time.gmtime(statinfo.st_mtime))
        headers['If-Modified-Since'] = last_mod_date
    else:
        # The file does not exist in the cache; let's fetch
        LOG.debug("We have not been able to find %s on disk." % filepath)

    req = requests.get(url, stream=True, timeout=(8, 24), headers=headers)

    if req.status_code == 200:
        if exists:
            # The file on the server is newer
            LOG.info("The local file was last modified in %s." % last_mod_date)
            LOG.info("The server's last modified in %s" % req.headers['last-modified'])
            LOG.info("We need to fetch it again.")

        _save_file(req, filename)

    elif req.status_code == 304:
        # The file on disk is recent
        LOG.debug("%s is on disk and it is current." % last_mod_date)

    else:
        raise Exception("We received %s which is unexpected." % req.status_code)

    try:
        if not MEMORY_SAVING_MODE:
            return _load_json_file(filepath)

        return _lean_load_json_file(filepath)

    # Issue 213: sometimes we download a corrupted builds-*.js file
    except IOError:
        LOG.info("%s is corrupted, we will have to download a new one.", filename)
        os.remove(filepath)
        return load_file(filename, url)


def _lean_load_json_file(filepath):
    """Helper function to load json contents from a file using ijson."""
    LOG.debug("About to load %s." % filepath)

    fd = open(filepath, 'r')

    gzipper = gzip.GzipFile(fileobj=fd)
    builds = ijson.items(gzipper, 'builds.item')
    ret = {'builds': []}
    # We are going to store only the information we need from builds-.js
    # and drop the rest.
    ret['builds'] = [
        {"properties": {
            "buildername": b["properties"].get("buildername", None),
            "request_ids": b["properties"].get("request_ids", []),
            "revision": b["properties"].get("revision", None)},
         "request_ids": b["request_ids"]}
        for b in builds]

    fd.close()
    gzipper.close()

    return ret
