Project Definition
##################
At Mozilla we have many parts that compose our Continous Integration systems.
Many of the parts of these systems have grown at different times, developed by many different
teams and not necessarily enough time to design a unified approach to them.

Mozilla CI Tools was born in order to help interact with the various parts of the CI
and accomplish much more sophisticated operations.

Various case scenarios will be described below in order to help understand the type
of solutions we want to design.

In order to understand better the data sources we use visit Data_Sources_.

Use cases
=========

Case scenario 1: Bisecting permanent issue
==========================================
* We have a job failing
* There are jobs that were coalesced between the last good and the first bad
* We need to backfill between changeset-good to changeset-bad

NOTE: How to handle a green intermittent! (corner case)
NOTE: Consider not having a build job since it was broken for few changesets and then an issue came up.
NOTE: Consider if a job is canceled or PGO or nightly.

Case scenario 2: Bisecting intermittent issue
==========================================
* We have an intermittent job
* We want to determine when it started happening
* It is not only a matter of coalescing but also a matter of frequency
* We want to give a range of changesets and bisect until spotting culprit

NOTE: We trigger more than once compared to case scenario 1

Case scenario 3: Retrigger an intermittent job on a changeset until hit
==========================================
https://bugzilla.mozilla.org/show_bug.cgi?id=844746

* This is more of an optimization.
* The intent is to hit the orange with extra debugging information.
* We're not bisecting in here.
* We can trigger batches (e.g. 5 at a time)

NOTE: Consider how to determine that the jobs have been completed (status of jobs)

Case scenario 4: Bisecting Talos
==========================================
* We have a performance regression
* We want to determine when it started showing up
* Given a revision that _failed_
* Re-trigger that revision three times and all revisions prior to it until the last data point + 1 more

Case scenario 5: After uplift we need a new baseline for release branches
==========================================
* We need several data points to establish a baseline
* After an uplift we need to generate a new baseline
* Once there is a baseline we can determine regression


Case scenario 6: New test validation
==========================================
* New test validation
* re-triggering to determine indeterminacy
* Single revision
* All platforms running test

Case scenario 7: Fill in a changeset
==========================================
* We know that a changeset is missing jobs
* We want to add all missing jobs

.. _Data_Sources: data_sources.html
