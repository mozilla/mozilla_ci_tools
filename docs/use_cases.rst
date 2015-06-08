Use cases
=========

.. contents:: Table of Contents
   :depth: 2
   :local:

Case scenario 1: Bisecting permanent issue
------------------------------------------
* We have a job failing
* There are jobs that were coalesced between the last good and the first bad job
* We need to backfill between good revision and the bad revision

This has been completed by the trigger.py with --backfill.

Case scenario 2: Bisecting intermittent issue
---------------------------------------------
* We have an intermittent job
* We want to determine when it started happening
* It is not only a matter of coalescing but also a matter of frequency
* We want to give a range of changesets and bisect until spotting culprit

NOTE: We trigger more than one job compared to case scenario 1

The script trigger.py helps with triggering multiple times the same jobs.
The script generate_cli.py helps with tracking filed intermittent oranges in bugzilla.

This use case requires implementing the following milestones:

* `Add the ability to find intermittent oranges`_
* `Allow monitoring jobs`_

Case scenario 3: Retrigger an intermittent job on a changeset until hit
-----------------------------------------------------------------------
https://bugzilla.mozilla.org/show_bug.cgi?id=844746

* This is more of an optimization.
* The intent is to hit the orange with extra debugging information.
* We're not bisecting in here.
* We can trigger batches (e.g. 5 at a time)

Not in scope at the moment.

This could be done with a modification of trigger.py where we monitor the jobs
running until one of them fails.

This use case requires implementing the following milestones:

* `Allow monitoring jobs`_

and this issue:

* `Add the ability to inspect the reason of a job failure`_

Case scenario 4: Bisecting Talos
--------------------------------
* We have a performance regression
* We want to determine when it started showing up
* Given a revision that _failed_
* Re-trigger that revision N times and all revisions prior to it until the last data point + 1 more

We can do this manually by using --back-revisions:::

  python scripts/trigger.py \
      --buildername "Rev5 MacOSX Yosemite 10.10 fx-team talos dromaeojs" \
      --rev e16054134e12 --back-revisions 10

We currently don't have the ability to determine the previous baseline and trigger everything up
to the last known data point close to the baseline.

Case scenario 5: After uplift we need a new baseline for release branches
-------------------------------------------------------------------------
* We need several data points to establish a baseline
* After an uplift we need to generate a new baseline
* Once there is a baseline we can determine regression

This can already be accomplished like this:::

  python alltalos.py --repo-name try --times 2 --rev 921277f744d9

Case scenario 6: New test validation
------------------------------------
* New test validation
* Re-triggering to determine indeterminacy
* Single revision
* All platforms running test

NOTE: Review `this thread`_ on how to determine on which job and which platforms do we run a specific test.

Not in scope at the moment.

Case scenario 7: Fill in a changeset
------------------------------------
* We know that a changeset is missing jobs
* We want to add all missing jobs

This would need grabbing the list of builders for such repo,
determine if there has been a successful job for each builder and trigger it if not.
We might need to filter out some periodic builders (i.e. a repo can have pgo periodic jobs).

If we want to watch that revision until it is completely filled we will need to accomplish the following milestones:

* `Allow monitoring jobs`_

Case scenario 8: Developer needs to add missing platforms/jobs for a Try push
-----------------------------------------------------------------------------
* The developer pushes to try specifying only a subset of all jobs
* The developer realizes that it needs more jobs to run on that push
* The developer uses mozci to not have to push again to try with the right syntax

This has been filed as `issue 109 <https://github.com/armenzg/mozilla_ci_tools/issues/109>`_

Case scenario 9: We generate data to build a dynamic TryChooser UI
------------------------------------------------------------------
* TryChooser UI is always out of date
* mozci can generate the data we need to create an up-to-date TryChooser UI

See `write_tests_per_platform_graph.py`_ for an example on how to generate the data needed.

.. _Add the ability to find intermittent oranges: https://github.com/armenzg/mozilla_ci_tools/milestones/Add%20the%20ability%20to%20find%20intermittent%20oranges
.. _Allow monitoring jobs: https://github.com/armenzg/mozilla_ci_tools/milestones/Allow%20monitoring%20jobs
.. _Add the ability to inspect the reason of a job failure: https://github.com/armenzg/mozilla_ci_tools/issues/128
.. _this thread: https://groups.google.com/forum/#!topic/mozilla.tools/7rEpVqBeui0
.. _write_tests_per_platform_graph.py: https://github.com/armenzg/mozilla_ci_tools/tree/master/scripts/misc/write_tests_per_platform_graph.py
