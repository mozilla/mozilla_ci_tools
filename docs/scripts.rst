Scripts
#######

The scripts directory contains various scripts that have various specific
uses and help drive the development of Mozilla CI tools.

trigger.py
^^^^^^^^^^
It simply helps you to trigger any job. It deals with missing jobs and determining
the job that triggered a test and/or talos jobs.::

    usage: trigger.py -b buildername --rev revision [OPTION]...

    optional arguments:
      -h, --help            show this help message and exit
      -b BUILDERNAME, --buildername BUILDERNAME
                            The buildername used in Treeherder
      --rev REVISION        The 12 character revision.
      --file FILES          Append files needed to run the job (e.g.installer,
                            test.zip)
      --debug               Print debugging information
      --dry-run             Do not make post requests.

trigger_range.py
^^^^^^^^^^^^^^^^
This script allows you to trigget a buildername many times across a range of pushes.
You can either:

a) give a start and end revision
b) go back N revisions from a given revision
c) use a range based on a delta from a given revision

::

    usage: trigger_range.py [-h] -b BUILDERNAME --times TIMES [--delta DELTA]
                            [--rev PUSH_REVISION] [--start-rev START]
                            [--end-rev END] [--back-revisions BACK_REVISIONS]
                            [--dry-run] [--debug]

    optional arguments:
      -h, --help            show this help message and exit
      -b BUILDERNAME, --buildername BUILDERNAME
                            The buildername used in Treeherder.
      --times TIMES         Number of times to retrigger the push.
      --delta DELTA         Number of jobs to add/subtract from push revision.
      --rev PUSH_REVISION   revision of the push.
      --start-rev START     The 12 character revision to start from.
      --end-rev END         The 12 character revision to start from.
      --back-revisions BACK_REVISIONS
                            Number of revisions to go back from current revision
                            (--rev).
      --dry-run             flag to test without actual push.
      --debug               set debug for logging.

generate_cli.py
^^^^^^^^^^^^^^^
This script allows you to generate a bunch of cli commands that would allow you to investigate
the revision to blame for an intermittent orange.
You have to specify the bug number for the intermittent orange you're investigating and this
script will you give you the scripts you need to run to backfill the jobs you need.

::

    usage: generate_triggercli.py [-h] [--bug-no BUG_NO] [--test-name TEST_NAME]
                                  --back-revisions BACK_REVISIONS --times TIMES

    optional arguments:
      -h, --help            show this help message and exit
      --bug-no BUG_NO       Provide the bug number to be searched.
      --test-name TEST_NAME
                            Provide the test-name and the script will output
                            command line forall intermittent bugs of that test-
                            name searched.
      --back-revisions BACK_REVISIONS
                            Number of revisions to go back from current revision
                            (--rev).
      --times TIMES         Number of times to retrigger the push.
