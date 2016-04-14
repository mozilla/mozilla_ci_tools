"""This script generates a list of buildbot test builders that are not triggered by any build."""
import logging

from mozci.platforms import determine_upstream_builder
from mozci.mozci import query_builders


logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()


def main():
    orphan_builders = []

    for builder in sorted(query_builders()):
        # To be fixed in issue 124
        if "l10n" in builder or "nightly" in builder:
            continue
        try:
            if determine_upstream_builder(builder) is None:
                orphan_builders.append(builder)
        except:
            orphan_builders.append(builder)

    for x in sorted(orphan_builders):
        print x


if __name__ == '__main__':
    main()
