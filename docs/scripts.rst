Scripts
#######

The scripts directory contains various scripts that have various specific
uses and help drive the development of Mozilla CI tools.

To be able to use these scripts all you have to do is this: ::

   git clone https://github.com/armenzg/mozilla_ci_tools.git
   python setup.py develop (or install)

trigger.py
^^^^^^^^^^
It simply helps trigger a job. It deals with missing jobs and determining
associated build jobs for test and talos jobs.


trigger_range.py
^^^^^^^^^^^^^^^^
This script allows you to trigger a buildername many times across a range of pushes.
You can either:

a) give a start and end revision
b) go back N revisions from a given revision
c) use a range based on a delta from a given revision


generate_triggercli.py
^^^^^^^^^^^^^^^^^^^^^^
This script allows you to generate a bunch of cli commands that would allow you to investigate
the revision to blame for an intermittent orange.
You have to specify the bug number for the intermittent orange you're investigating and this
script will you give you the scripts you need to run to backfill the jobs you need.


alltalos.py
^^^^^^^^^^^
This script runs all the talos jobs for a given branch/revision.  Usage:
  --repo-name REPO_NAME
                        The name of the repository: e.g. 'cedar'.
  --times TIMES         Number of times to retrigger the push.
  --rev REVISION        revision of the push.
  --dry-run             flag to test without actual push (optional).
  --debug               set debug for logging (optional).
  --pgo                 trigger pgo tests (not non-pgo) (optional).
