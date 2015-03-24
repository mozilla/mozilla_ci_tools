import logging

from mozci.utils.transfer import fetch_file

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)

filename = "builds-2015-03-24.js"
url = "http://builddata.pub.build.mozilla.org/builddata/buildjson/%s.gz" % filename

fetch_file(filename, url)
