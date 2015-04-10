import gzip
import json
import logging
import os
import shutil
import time
import StringIO

from tempfile import NamedTemporaryFile

import requests

from progressbar import Bar, Timer, FileTransferSpeed, ProgressBar

LOG = logging.getLogger()


def path_to_file(filename):
    """Add files to .mozilla/mozci"""
    path = os.path.expanduser('~/.mozilla/mozci/')
    if not os.path.exists(path):
        os.makedirs(path)
    filepath = os.path.join(path, filename)
    return filepath


def _fetch_and_load_file(req, filename):
    """
    Helper private function to simply download a file, to show its progress and to verify
    that is valid json.
    """
    if not os.path.isabs(filename):
        filename = path_to_file(filename)

    LOG.debug("About to fetch %s from %s" % (filename, req.url))

    size = int(req.headers['Content-Length'].strip())
    blob = ""
    bytes = 0

    widgets = [
        os.path.basename(filename), ": ",
        Bar(marker=">", left="[", right="]"), ' ',
        Timer(), ' ',
        FileTransferSpeed(), " ",
        "{0}MB".format(round(size / 1024 / 1024, 2))
    ]
    pbar = ProgressBar(widgets=widgets, maxval=size).start()
    for chunk in req.iter_content(10 * 1024):
        if chunk:  # filter out keep-alive new chunks
            blob += chunk
            bytes += len(chunk)
            pbar.update(bytes)
    pbar.finish()

    if req.headers['Content-Encoding'] == 'x-gzip':
        if filename.endswith('.gz'):
            filename = filename[:-3]
        LOG.debug("Let's decompress the received data.")
        compressed_stream = StringIO.StringIO(blob)
        gzipper = gzip.GzipFile(fileobj=compressed_stream)
        blob = gzipper.read()

    try:
        # This will raise an JsonDecoderException if it is not valid json
        json_content = json.loads(blob)
    except ValueError:
        LOG.error("The obtained json from %s got corrupted. Try again." % req.url)
        exit(1)

    LOG.debug("Writing to temp file.")
    temp_file = NamedTemporaryFile(delete=False)
    with open(temp_file.name, 'wb') as fd:
        json.dump(json_content, fd)

    LOG.debug("Moving %s to %s" % (temp_file.name, filename))
    shutil.move(temp_file.name, filename)

    return json_content


def load_file(filename, url):
    """
    We download a file without decompressing it so we can keep track of its progress.
    We save it to disk and return the contents of it.
    We also check if the file on the server is newer to determine if we should download it again.

    raises Exception if anything goes wrong.
    """
    # Obtain the absolute path to our file in the cache
    if not os.path.isabs(filename):
        filepath = path_to_file(filename)
    else:
        filepath = filename

    if os.path.exists(filepath):
        # The file exists in the cache, let's verify that is still current
        statinfo = os.stat(filepath)
        last_mod_date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(statinfo.st_mtime))

        req = requests.get(url, stream=True, timeout=(8, 24),
                           headers={'If-Modified-Since': last_mod_date, 'Accept-Encoding': None})

        if req.status_code == 200:
            # The file on the server is newer
            LOG.debug("The local file was last modified in %s. We need to delete the file and fetch it again." % last_mod_date)
            os.remove(filepath)
            return _fetch_and_load_file(req, filepath)
        elif req.status_code == 304:
            # The file on disk is recent
            LOG.debug("%s is on disk and it is current." % last_mod_date)
            LOG.debug("About to load %s." % filepath)
            try:
                return json.load(open(filepath))
            except ValueError, e:
                LOG.exception(e)
                new_file = filepath + ".corrupted"
                shutil.move(filepath, new_file)
                LOG.error("The file on-disk does not have valid data")
                LOG.info("We have moved %s to %s for inspection." % (filepath, new_file))
                exit(1)
        else:
            raise Exception("We received %s which is unexpected." % req.status_code)
    else:
        # The file does not exist in the cache; let's fetch
        LOG.debug("We have not been able to find %s on disk." % filepath)
        req = requests.get(url, stream=True, timeout=(8, 24), headers={'Accept-Encoding': None})
        return _fetch_and_load_file(req, filepath)
