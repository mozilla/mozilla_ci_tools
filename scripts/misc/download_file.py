# This script simply tests that we can download a file
import json
import logging
import shutil

from argparse import ArgumentParser

from mozci.utils.transfer import fetch_file, path_to_file

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('url', type=str)
    options = parser.parse_args()

    filename = options.url.split("/")[-1]
    fetch_file(filename, options.url)

    filepath = path_to_file(filename)

    LOG.debug("About to load %s." % filepath)
    try:
        builds = json.load(open(filepath))["builds"]
    except ValueError, e:
        LOG.exception(e)
        new_file = filename + ".corrupted"
        shutil.move(filepath, new_file)
        LOG.error("The file on-disk does not have valid data")
        LOG.info("We have moved %s to %s for inspection." % (filepath, new_file))
