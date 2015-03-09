Roadmap
=======

.. contents:: Table of Contents
   :depth: 2
   :local:

Create prototype to trigger N jobs for a range of revisions
-----------------------------------------------------------
This allows backfilling jobs.

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
known good job for it. Known that, we can trigger all jobs require to coverage
the missing jobs.

This feature was completed on release 0.3.0.

Ability to navigate through merges into other repositories
----------------------------------------------------------
We need the ability to navigate through pushes and be able to follow
through from one repository to another when merge pushes are found.

This is important to find an intermittent failing job.

Make handling Buildbot job information sustainable
--------------------------------------------------
We currently have information about Buildbot jobs by grabbing scheduling info
and status info. This is something that users should never know about.
We should only expose the bits of information which are relevant to the user and
allow them to access the raw data only if wished for.

Adding a base class to abstract jobs and have one implementation for Buildbot
will make the project ready for the representation of jobs in TaskCluster.

Test framework to test CI data sources
--------------------------------------
We need to have a way to prevent regressions on Mozilla CI tools.
Adding coverage reports would help us fix this issue.

We also need a way to test the data sources structures for changes that could regress us
(e.g. new builder naming for Buildbot).
We might be able to simply mock it but we might need to set up the various data sources.

This is to be tackled in Q2/Q3 2015.

Provide data to generate up-to-date trychooser
----------------------------------------------
Currently trychooser's UI is always out-of-date and nothing intelligent can be done with it.
With mozci we currently can generate most of the data necessary to create a dynamic UI.

Integrate backfilling feature into treeherder
---------------------------------------------
This will be similar to the re-trigger button that is part of the treeherder UI.
We select a job that is failing and request that we backfill.
mozci will determine when was the last time there was a successful job and trigger
all missing jobs up to the last known good job.

TreeHerder currently uses client-side triggering for the re-trigger button and it
intends to move it to the server side (`bug 1077053 <https://bugzilla.mozilla.org/show_bug.cgi?id=1077053>`_).

We have filed a TreeHerderissue 109 <https://github.com/armenzg/mozilla_ci_tools/issues/109>

Allow inspecting for the reason of a suite failure
--------------------------------------------------
When chasing an intermittent orange test, we need inspect which tests failed for a suite.
By doing this we can determine if an orange job should be counted when searching for
a specific intermittent test.

Determine frequency of test failure
-----------------------------------
We need to find a way to analyze test failure frequency.
That way we can determine the right number of jobs of to retrigger a job
in order to find an intermittent orange.

Produce data structure for monitoring
-------------------------------------
This would be useful to help us monitor jobs that:

* get triggered
* could be triggered
* expect to be triggered after an upstream job finishes

Allow a user to monitor jobs triggered
--------------------------------------
We currently trigger jobs and don’t have an standardized method to monitor such triggered jobs.
We have buildapi, buildjson, builds-running, builds-pending and treeherder APIs as our source
candidates.

Support TaskCluster
-------------------
As we're transitioning to TaskCluster we should add the support for it.
