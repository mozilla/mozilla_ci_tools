Use cases
=========

Case scenario 1: Bisecting permanent issue
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* We have a job failing
* There are jobs that were coalesced between the last good and the first bad job
* We need to backfill between good revision and the bad revision

This has been completed by the trigger_range.py.

Case scenario 2: Bisecting intermittent issue
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* We have an intermittent job
* We want to determine when it started happening
* It is not only a matter of coalescing but also a matter of frequency
* We want to give a range of changesets and bisect until spotting culprit

NOTE: We trigger more than one job compared to case scenario 1

The script trigger_range.py helps with triggering multiple times the same jobs.
The script generate_cli.py helps with tracking filed intermittent oranges in bugzilla.

Case scenario 3: Retrigger an intermittent job on a changeset until hit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
https://bugzilla.mozilla.org/show_bug.cgi?id=844746

* This is more of an optimization.
* The intent is to hit the orange with extra debugging information.
* We're not bisecting in here.
* We can trigger batches (e.g. 5 at a time)

Not in scope at the moment.

This could be done with a modification of trigger.py where we monitor the jobs
running until one of them fails.

The monitoring module would help with this.

Case scenario 4: Bisecting Talos
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* We have a performance regression
* We want to determine when it started showing up
* Given a revision that _failed_
* Re-trigger that revision N times and all revisions prior to it until the last data point + 1 more

NOTE: Ask jmaher if he already has implemented this.

Case scenario 5: After uplift we need a new baseline for release branches
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* We need several data points to establish a baseline
* After an uplift we need to generate a new baseline
* Once there is a baseline we can determine regression

NOTE: Ask jmaher if he already has implemented this.

The scripts trigger.py and trigger_range.py would be suitable for this.

Case scenario 6: New test validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* New test validation
* Re-triggering to determine indeterminacy
* Single revision
* All platforms running test

NOTE: I don't know how to determine on which job and which platforms we run a specific test.

Not in scope at the moment.

Case scenario 7: Fill in a changeset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* We know that a changeset is missing jobs
* We want to add all missing jobs

Not in scope at the moment.
