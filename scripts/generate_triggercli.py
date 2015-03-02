'''
General Workflow for this script:
1)  Feed parameters to generate_triggercli.py to generate the command line
    used to trigger intermittents via trigger_range.py

    Example:
    python <your_dir_path>/generate_triggercli.py --back-revisions=3 --times=3 --bug-no=1133456

    This will output:

    INFO:    Starting new HTTPS connection (1): bugzilla.mozilla.org
    INFO:    Here are the command line(s) you need for triggering the jobs
             to find root cause of intermittent.
    INFO:    python /home/vaibhav/mozilla_ci_tools/scripts/trigger_range.py --rev=89e49bd65079
             --back-revisions=3
             --buildername='Ubuntu VM 12.04 x64 mozilla-inbound debug test mochitest-3'
             --times=3 --debug --dry-run


2) Use the above given commandline to test out on local machine.
   Yes, --dry-run is there for testing the above cli output generated.

3) Remove the --dry-run parameter and actually trigger intermittents via trigger_range.py script
'''
import bugsy
import logging
import os
from argparse import ArgumentParser
from mozci.mozci import query_repo_name_from_buildername

bugzilla = bugsy.Bugsy()
logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()
LOG.setLevel(logging.INFO)


def parse_args(argv=None):
    '''
    Parse command line options.
    '''
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

    options = parser.parse_args(argv)
    return options


def check_repository(buildername):
    '''
    Function to check if the repository in buildername matches the supported repositories.
    '''
    supported_repositories = ['fx-team', 'mozilla-inbound', 'mozilla-aurora']
    repo_name = query_repo_name_from_buildername(buildername)
    if repo_name not in supported_repositories:
        raise Exception('The script supports only for fx-team, mozilla-inbound, mozilla-aurora')

    return repo_name


def generate_cli(search_dict, back_revisions, times=20):
    '''
    Generate command line for triggering a range of revisions.
    '''
    LOG.info("Here are the command line(s) you need for "
             "triggering the jobs to find root cause of intermittent:")
    for bname, rev in search_dict.iteritems():
        check_repository(bname)
        LOG.info("python %s/trigger_range.py "
                 "--rev=%s --back-revisions=%s --buildername='%s' "
                 "--times=%s --debug --dry-run" %
                 (os.getcwd(), rev, back_revisions, bname, times))


def search_bug(bug_no):
    '''
    Search a given bug number to return the buildername and revision of first tbpl bot comment.
    A typical comment looks like this for example:

    log: https://treeherder.mozilla.org/logviewer.html#?repo=mozilla-inbound&job_id=6640081
    repository: mozilla-inbound
    start_time: 2015-02-15T20:13:14
    who: tomcat[at]mozilla[dot]com
    machine: tst-linux64-spot-1026
    buildname: Ubuntu VM 12.04 x64 mozilla-inbound debug test mochitest-3
    revision: 89e49bd65079
    '''
    bug = bugzilla.get(bug_no)
    search_dict = {}

    try:
        for comment in bug.get_comments():
            if comment.creator == "tbplbot@gmail.com":
                # Limiting to first comment by tbpl bot because we want to find the first revision
                # where the regression occured.
                first_comment = comment.text
                break
    except:
        Exception("Issue getting comments for bug %s" % bug.id)

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
    options = parse_args()
    bugs = []
    if options.bug_no:
        bugs.append(options.bug_no)

    if options.test_name:
        buglist = bugzilla.search_for\
            .summary(options.test_name)\
            .keywords("intermittent-failure")\
            .search()
        for bug in buglist:
            bugs.append(bug.id)

    for bug_no in bugs:
        search_dict = search_bug(bug_no)
        generate_cli(search_dict, options.back_revisions, options.times)
