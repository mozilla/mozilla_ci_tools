Roadmap
=======

**NOTE** This roadmap needs to be reviewed.

Milestones
----------
Create prototype to trigger N jobs for a range of revisions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This allows backfilling jobs.

This has been accomplished on the 0.2.1 release (13/02/2015).

Add pushlog support
^^^^^^^^^^^^^^^^^^^
This helps interacting with ranges of revisions.

This has been accomplished on the 0.2.1 release (13/02/2015).

Determine accurately the current state of jobs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We can determine any information on jobs run on the Buildbot CI by retrieving
scheduling information through Self-Serve's BuildAPI.
The information retrieved can then be matched to the buildjson status dumps that
are produced every minute (for the last 4 hours) and every 15 minutes (for the day's worth of
data).

This feature is close to completion. Only issue 46 is left (25/02/2015).

Create prototype to backfill
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Given a bad job, we can simply to scan the previous revisions for the last
known good job for it. Known that, we can trigger all jobs require to coverage
the missing jobs.

Integrate backfilling feature into treeherder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This will be similar to the re-trigger button that is part of the treeherder UI.
We select a job that is failing and request that we backfill.
mozci will determine when was the last time there was a successful job and trigger
all missing jobs up to the last known good job.

Produce data structure for monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This would be useful to help us monitor jobs that:

* get triggered
* could be triggered
* expect to be triggered after an upstream job finishes

Allow a user to monitor jobs triggered
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We currently trigger jobs and don’t have an standardized method to monitor such triggered jobs.
We have buildapi, buildjson, builds-running, builds-pending and treeherder APIs as our source
candidates.

Test framework to test CI data sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We need to have a way to prevent regressions on Mozilla CI tools.
Adding coverage reports would help us fix this issue.

We also need a way to test the data sources structures for changes that could regress us
(e.g. new builder naming for Buildbot).
We might be able to simply mock it but we might need to set up the various data sources.

This is to be tackled in Q2/Q3 2015.
