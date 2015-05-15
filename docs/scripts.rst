Scripts
#######

The scripts directory contains various scripts that have various specific
uses and help drive the development of Mozilla CI tools. All the scripts are
located in mozci/scripts directory.

For each script, separate instructions are given if you have installed mozci via:

1) "pip install" or
2) Cloned the repository from source for development purposes

trigger.py
^^^^^^^^^^
This script allows you to trigger a buildername many times across a range of pushes.
You can either:

a) give a start and end revision
b) go back N revisions from a given revision
c) use a range based on a delta from a given revision
d) find the last good known job and trigger everything missing up to it

If you have done "pip install", run via commandline::

  $ mozci-trigger

In cloned repository for development::

  $ python trigger.py

Usage::

  usage: trigger.py [-h] -b BUILDERNAME -r REV [--times TIMES] [--skips SKIPS]
                    [--from-rev FROM_REV] [--max-revisions MAX_REVISIONS]
                    [--dry-run] [--debug] [--delta DELTA]
                    [--back-revisions BACK_REVISIONS] [--backfill]

  optional arguments:
    -h, --help            show this help message and exit
    -b BUILDERNAME, --buildername BUILDERNAME
                          The buildername used in Treeherder.
    -r REV, --revision REV
                          The 12 character representing a revision (most
                          recent).
    --times TIMES         Number of times to retrigger the push.
    --skips SKIPS         Specify the step size to skip after every retrigger.
    --from-rev FROM_REV   The 12 character representing the oldest push to start
                          from.
    --max-revisions MAX_REVISIONS
                          This flag is used with --backfill. This flag limitshow
                          many revisions we will look back until we findthe last
                          revision where there was a good job.
    --dry-run             flag to test without actual push.
    --debug               set debug for logging.
    --delta DELTA         Number of jobs to add/subtract from push revision.
    --back-revisions BACK_REVISIONS
                          Number of revisions to go back from current revision
                          (--rev).
    --backfill            We will trigger jobs starting from --rev in reverse
                          chronological order until we find the last revision
                          where there was a good job.

alltalos.py
^^^^^^^^^^^
This script runs all the talos jobs for a given branch/revision.

If you have done "pip install", run via commandline::

  $ mozci-alltalos

In cloned repository for development::

  $ python alltalos.py

Usage::

  usage: alltalos.py [-h] --repo-name REPO_NAME --times TIMES [--rev REVISION]
                     [--dry-run] [--debug] [--pgo]

  optional arguments:
    -h, --help            show this help message and exit
    --repo-name REPO_NAME
                          The name of the repository: e.g. 'cedar'.
    --includes INCLUDES   comma-separated treeherder filters to include.
    --exclude EXCLUDE     comma-separated treeherder filters to exclude.
    --times TIMES         Number of times to retrigger the push.
    --rev REVISION        revision of the push.
    --dry-run             flag to test without actual push.
    --debug               set debug for logging.
    --pgo                 trigger pgo tests (not non-pgo).

generate_triggercli.py
^^^^^^^^^^^^^^^^^^^^^^
This script allows you to generate a bunch of cli commands that would allow you to investigate
the revision to blame for an intermittent orange.
You have to specify the bug number for the intermittent orange you're investigating and this
script will you give you the scripts you need to run to backfill the jobs you need.

misc/write_tests_per_platform_graph.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This script generates a graph of every platform and test in try.

The graph contains two main keys: 'opt' and 'debug'. Inside each there
is a key for each platform.

For every platform there is a key for every upstream builder,
containing a list of its downstream builders and a key 'tests' that
contains a list of every test that is run in that platform.

For example, the key 'android-x86' in 'opt' is::

  "android-x86": {
            "Android 4.2 x86 try build": [
                "Android 4.2 x86 Emulator try opt test androidx86-set-4"
            ],
            "tests": ["androidx86-set-4"]
        },

This script is run nightly and its output can be found at
http://people.mozilla.org/~armenzg/permanent/graph.json

If you could use a graph like this but the current format is not
ideal, please `file an issue
<https://github.com/armenzg/mozilla_ci_tools/issues>`_.

triggerbyfilters.py
^^^^^^^^^^^^^^^^^^^

This script retriggers N times every job that matches --includes and doesn't match --exclude.

If you have done "pip install", run via commandline::

  $ mozci-triggerbyfilters

In cloned repository for development::

  $ python triggerbyfilters.py

Usage::

  usage: th_filters.py [-h] REPO REVISION -i INCLUDES [-e EXCLUDE]
                       [--times TIMES] [--limit LIM] [--dry-run] [--debug]

  positional arguments:
    repo                  Branch name
    rev                   The 12 character representing a revision (most
                          recent).

  optional arguments:
    -h, --help            show this help message and exit
    -i INCLUDES, --includes INCLUDES
                          comma-separated treeherder filters to include.
    -e EXCLUDE, --exclude EXCLUDE
                          comma-separated treeherder filters to exclude.
    --times TIMES         Number of times to retrigger the push.
    --limit LIM           Maximum number of buildernames to trigger.
    --dry-run             flag to test without actual push.
    --debug               set debug for logging.


For example, if you want to retrigger all web-platform-tests on cedar in a debug platform 5 times::

  python triggerbyfilters.py cedar REVISION --includes "web-platform-tests,debug" --times 5

If you want the same thing but without web-platform-tests-2::

  python triggerbyfilters.py cedar REVISION --includes "web-platform-tests,debug" --exclude "web-platform-tests-2" --times 5

Note: this script currently only does string matching on buildernames, so some queries may not be supported. If you encounter any problem, please `file an issue
<https://github.com/armenzg/mozilla_ci_tools/issues>`_.
