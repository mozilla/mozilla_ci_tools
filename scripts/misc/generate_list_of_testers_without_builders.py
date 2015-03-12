'''
This script generates a list of buildbot test builders that do not
have a build to trigger it.
'''
import logging

from mozci.platforms import determine_upstream_builder
from mozci.mozci import query_builders


logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()


def main():
    list = []

    for builder in sorted(query_builders()):
        # To be fixed in issue 124
        if "l10n" in builder or "nightly" in builder:
            continue

        if determine_upstream_builder(builder) is None:
            list.append(builder)

    for x in sorted(list):
        print x


if __name__ == '__main__':
    main()
