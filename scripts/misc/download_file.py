# This script simply tests that we can download a file
import logging

from argparse import ArgumentParser

from mozci.utils.transfer import load_file

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('url', type=str)
    options = parser.parse_args()

    filename = options.url.split("/")[-1]
    json_contents = load_file(filename, options.url)

    builds = json_contents["builds"]
