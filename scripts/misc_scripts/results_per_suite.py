"""This script generates a csv table with the success rates for tests in a platform."""
import csv
import json

import requests

from argparse import ArgumentParser

ACTIVEDATA_URL = "http://activedata.allizom.org/query"


def get_query(repo_name):
    query = {"from": "unittest",
             "groupby": ["build.name", "run.buildbot_status"],
             "limit": 10000,
             "where": {"and": [
                 {"eq": {"etl.id": 0}},
                 {"eq": {"build.branch": repo_name}}
             ]}}
    return json.dumps(query)


def parse_arguments(argv=None):
    """Get the branch name from the command line."""
    parser = ArgumentParser()
    parser.add_argument("repo",
                        help="Branch name")
    return parser.parse_args(argv)


def main():
    options = parse_arguments()
    # Querying ActiveData
    req = requests.post(ACTIVEDATA_URL, data=get_query(options.repo))
    values = req.json()['data']

    # Making a table with the values we obtained
    builders = {}
    for value in values:
        if value[0] not in builders:
            builders[value[0]] = {
                'success': 0,
                'warnings': 0,
                'failure': 0,
                'retry': 0,
                'exception': 0,
                'cancelled': 0,
                'total': 0
            }

        builders[value[0]][value[1]] = int(value[2])
        builders[value[0]]['total'] += int(value[2])

    # Writing results to a file
    filename = 'results_per_suite_%s.csv' % options.repo
    with open(filename, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            ['Buildername', 'Success', 'Warnings',
             'Failure', 'Retry', 'Exception',
             'Cancelled', 'Success rate'])

        # Computing success rates
        for buildername, values in builders.iteritems():
            builders[buildername]['success rate'] = 100.0 * (values['success']) / (values['total'])

        for buildername in sorted(builders.keys(),
                                  key=lambda b: builders[b]['success rate']):
            values = builders[buildername]
            writer.writerow(
                [
                    buildername,
                    values['success'],
                    values['warnings'],
                    values['failure'],
                    values['retry'],
                    values['exception'],
                    values['cancelled'],
                    "%.2f%%" % values['success rate']
                ])


if __name__ == '__main__':
    main()
