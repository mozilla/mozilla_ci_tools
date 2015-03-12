Roadmap
=======

.. contents:: Table of Contents
   :depth: 2
   :local:

Create prototype to trigger N jobs for a range of revisions
-----------------------------------------------------------
This allows triggering multiple jobs across a range of revisions.

Here's an example: ::

  python scripts/trigger.py \
      --buildername "Ubuntu VM 12.04 fx-team opt test jittest-1" \
      --rev e16054134e12 --from-rev fb64168bf663 --times 2

This has been accomplished on the 0.2.1 release (13/02/2015).

Add pushlog support
-------------------
This helps interacting with ranges of revisions.

This has been accomplished on the 0.2.1 release (13/02/2015).

Determine accurately the current state of jobs
----------------------------------------------
We can determine any information on jobs run on the Buildbot CI by retrieving
scheduling information through Self-Serve's BuildAPI.
The information retrieved can then be matched to the buildjson status dumps that
are produced every minute (for the last 4 hours) and every 15 minutes (for the day's worth of
data).

This feature is completed. (25/02/2015).

Create prototype to find last good job and backfill up to it
------------------------------------------------------------
Given a bad job, we can simply scan the previous revisions for the last
known good job for it. Known that, we can trigger all jobs required to trigger the
missing jobs.

The script will find the last good job or trigger up to a maximum of revisions.
We can also indicate that we want multiple jobs instead of just one.

Here's an example: ::

  python scripts/trigger.py \
      --buildername "Ubuntu VM 12.04 fx-team opt test jittest-1" \
      --rev e16054134e12 --backfill --max-revisions 30 --times 2

This feature was completed on release 0.3.0.

Ability to navigate through merges into other repositories
----------------------------------------------------------
We need the ability to navigate through pushes and be able to follow
through from one repository to another when merge pushes are found.

This is important to find an intermittent failing job.

We have filed `issue 127`_ to track this.

.. _issue 127: https://github.com/armenzg/mozilla_ci_tools/issues/127

Determine if a test failed in a job
-----------------------------------
We currently can only tell if a job has failed, however, we don't know
which test(s) have failed.

If we want to find intermittent oranges we would need to determine if a job
has failed because the test we care about has actually failed.

A possible way to determine this would be to grab the `structured log`_
uploaded through blobber_.

**NOTE**: Reftests currently don't generate structured logs. In such case
we would have to fallback to parsing logs. We would have to request this to be
implemented.

**NOTE 2**: In the future, we might be able to query this information through the big
data project.

We have filed `issue 128`_ to track this.

.. _structured log: http://mozbase.readthedocs.org/en/latest/mozlog_structured.html
.. _blobber: https://github.com/mozilla/build-blobber
.. _issue 128: https://github.com/armenzg/mozilla_ci_tools/issues/128

Determine frequency of test failure
-----------------------------------
We need to find a way to analyze test failure frequency.
That way we can determine the right number of jobs of to retrigger a job
in order to find an intermittent orange.

I'm not sure if this will really be needed. We will see.

Make handling Buildbot job information sustainable
--------------------------------------------------
We currently have information about Buildbot jobs by grabbing scheduling info
and status info. This is something that users should never know about.
We should only expose the bits of information which are relevant to the user and
allow them to access the raw data only if wished for.

Adding a base class to abstract jobs and have one implementation for Buildbot
will make the project ready for the representation of jobs in TaskCluster.

We have filed `issue 21`_ to track this.

.. _issue 21: https://github.com/armenzg/mozilla_ci_tools/issues/21

Paralellize the analysis of each revision
-----------------------------------------
We currently iterate and analyze one revision at a time.
In many places we can parallelize this process since they're isolated
processes.

This will speed up the execution time.

**NOTES:**

* We should only print to the log once a revision has been completely processed.
* We should not print the summary about a revision until all most recent
  revisions are processed first.

    * i.e. log them in descending order based on their push id.
    * This will ensure that inspecting the log will visually make sense

We have filed `issue 129`_ to track this.

.. _issue 129: https://github.com/armenzg/mozilla_ci_tools/issues/129

Test framework to test CI data sources
--------------------------------------
We need to have a way to prevent regressions on Mozilla CI tools.
Adding coverage reports would help us fix this issue.

We also need a way to test the data sources structures for changes that could regress us
(e.g. new builder naming for Buildbot).
We might be able to simply mock it but we might need to set up the various data sources.

This is to be tackled in Q2/Q3 2015.

We have filed `issue 130`_ to track this.

.. _issue 130: https://github.com/armenzg/mozilla_ci_tools/issues/130

Provide data structure to generate up-to-date trychooser
--------------------------------------------------------
Currently trychooser's UI is always out-of-date and nothing intelligent can be done with it.
With mozci we currently can generate most of the data necessary to create a dynamic UI.

To generate the current data structure you can run this:::

  python scripts/misc/write_tests_per_platform_graph.py

graphs.json will be generated.
We have filed `issue 69`_ to track this.

**NOTE:** This will be needeed once someone picks up `bug 983802`_.

.. _bug 983802 : https://bugzilla.mozilla.org/show_bug.cgi?id=983802
.. _issue 69: https://github.com/armenzg/mozilla_ci_tools/issues/69

Integrate backfilling feature into treeherder
---------------------------------------------
This will be similar to the re-trigger button that is part of the treeherder UI.
We select a job that is failing and request that we backfill.
mozci will determine when was the last time there was a successful job and trigger
all missing jobs up to the last known good job.

TreeHerder currently uses client-side triggering for the re-trigger button and it
intends to move it to the server side (`bug 1077053`_).

We have filed `issue 109`_ to track this.

.. _bug 1077053: https://bugzilla.mozilla.org/show_bug.cgi?id=1077053
.. _issue 109: https://github.com/armenzg/mozilla_ci_tools/issues/109

Pulse support
-------------
Pulse allows you to listen and consume about jobs changing status.
This is very important for monitoring jobs going through various states.

We have filed `issue 126`_ to track this.

.. _issue 126 : https://github.com/armenzg/mozilla_ci_tools/issues/126

Add ability to monitor jobs
---------------------------
We currently run a script and let it schedule everything that is needed.
However, we assume an ideal case scenario: **everything that we schedule gets run**.

This is a very optimistic approach.  We should allow the user to use a mode
in which the script watches and notifies the user when our expectations are not met.

For instance:

* A build finishes, however, the tests that is expected to run gets coalesced

  * In this case we would be expecting a completed build job + a completed test job
  * We would need to schedule the test job and watch it

* A job fails, however, we assume it would succeed

  * We need to re-trigger it and watch it

We have filed `issue 131`_ to track this.

.. _issue 131: https://github.com/armenzg/mozilla_ci_tools/issues/131

Support TaskCluster
-------------------
As we're transitioning to TaskCluster we should add the support for it.

We are tracking this with the `TaskCluster Support`_ milestone.

.. _TaskCluster Support: https://github.com/armenzg/mozilla_ci_tools/milestones/TaskCluster%20support
