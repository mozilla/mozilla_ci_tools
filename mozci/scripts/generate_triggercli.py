"""
This script allows you to find an intermittent orange.
You can point the script to either the bug where the failures are being reported
or by indicating the test name.
The script will give you a list of commands to run to help you narrow down
where the intermittent orange was introduced.

NOTE: You run this script and you get a bunch of commands to run.

General Workflow for this script:
1)  Feed parameters to generate_triggercli.py to generate the command line
    used to trigger intermittents via trigger.py

    Example:
    python <your_dir_path>/generate_triggercli.py --back-revisions=3 --times=3 --bug-no=1133456

    This will output:

    INFO:    Starting new HTTPS connection (1): bugzilla.mozilla.org
    INFO:    Here are the command line(s) you need for triggering the jobs
             to find root cause of intermittent.
    INFO:    python scripts/trigger.py --rev=89e49bd65079
             --back-revisions=3
             --buildername='Ubuntu VM 12.04 x64 mozilla-inbound debug test mochitest-3'
             --times=3 --dry-run


2) Use the above given commandline to test out on local machine.
   Yes, --dry-run is there for testing the above cli output generated.

3) Remove the --dry-run parameter and actually trigger intermittents via trigger.py script.
"""
import logging
import os

from argparse import ArgumentParser

import bugsy

from mozci.mozci import query_repo_name_from_buildername
from mozci.utils.misc import setup_logging

bugzilla = bugsy.Bugsy()
LOG = setup_logging()


def main():
    global LOG

    options = parse_args()
    bugs = []
    assert options.bug_no or options.test_name, \
        "Either call this with --bug-no or with --test-name"

    if options.debug:
        LOG = setup_logging(logging.DEBUG)

    if options.bug_no:
        bugs.append(options.bug_no)

    if options.test_name:
        buglist = bugzilla.search_for.summary(
            options.test_name).keywords("intermittent-failure").search()
        for bug in buglist:
            bugs.append(bug.id)

    for bug_no in bugs:
        search_dict = search_bug(bug_no)
        generate_cli(search_dict, options.back_revisions, options.times)


def parse_args(argv=None):
    """Parse command line options."""
    parser = ArgumentParser()

    parser.add_argument("--bug-no",
                        dest="bug_no",
                        type=int,
                        help="Provide the bug number to be searched."
                        )

    parser.add_argument("--test-name",
                        dest="test_name",
                        help="Provide the test-name and the script will output command line for"
                             "all intermittent bugs of that test-name searched."
                        )

    parser.add_argument("--back-revisions",
                        dest="back_revisions",
                        required=True,
                        type=int,
                        help="Number of revisions to go back from current revision (--rev)."
                        )

    parser.add_argument("--times",
                        dest="times",
                        required=True,
                        type=int,
                        help="Number of times to retrigger the push.")

    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help="set debug for logging.")

    options = parser.parse_args(argv)
    return options


def check_repository(buildername):
    """Function to check if the repository in buildername matches the supported repositories."""
    supported_repositories = ['fx-team', 'mozilla-inbound', 'mozilla-aurora']
    repo_name = query_repo_name_from_buildername(buildername)
    if repo_name not in supported_repositories:
        raise Exception('The script supports only for fx-team, mozilla-inbound, mozilla-aurora')

    return repo_name


def generate_cli(search_dict, back_revisions, times=20):
    """Generate command line for triggering a range of revisions."""
    LOG.info("Here are the command line(s) you need for "
             "triggering the jobs to find root cause of intermittent:")
    for bname, rev in search_dict.iteritems():
        check_repository(bname)
        # Using print instead of logging to make it easier to copy/paste
        print "python %s/trigger.py " \
              "--rev=%s --back-revisions=%s --buildername='%s' " \
              "--times=%s --dry-run" % (os.getcwd(), rev, back_revisions, bname, times)


def search_bug(bug_no):
    """
    Search a given bug number to return the buildername and revision of first tbpl bot comment.
    A typical comment looks like this for example:

    log: https://treeherder.mozilla.org/logviewer.html#?repo=mozilla-inbound&job_id=6640081
    repository: mozilla-inbound
    start_time: 2015-02-15T20:13:14
    who: tomcat[at]mozilla[dot]com
    machine: tst-linux64-spot-1026
    buildname: Ubuntu VM 12.04 x64 mozilla-inbound debug test mochitest-3
    revision: 89e49bd65079
    """
    bug = bugzilla.get(bug_no)
    search_dict = {}

    try:
        for comment in bug.get_comments():
            if comment.creator == "tbplbot@gmail.com":
                # Limiting to first comment by tbpl bot because we want to find the first revision
                # where the regression occurred.
                first_comment = comment.text
                break
    except:
        raise Exception("Issue getting comments for bug %s" % bug.id)

    buildername = None
    rev = None
    lines = first_comment.split('\n')
    for line in lines:
        if line.startswith('buildname'):
            buildername = line.split('buildname: ')[1]
        elif line.startswith('revision'):
            rev = line.split('revision: ')[1]

    if buildername and rev:
        if buildername not in search_dict:
            search_dict[buildername] = rev

    return search_dict


if __name__ == "__main__":
    main()
