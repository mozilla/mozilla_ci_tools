F.A.Q.
======

I asked mozci to trigger a test job for me, however, a build got triggered
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Test jobs require a build to be tested, hence, needing to trigger a build for it.

In some cases you might see that a build exists for that push and still trigger a build.
This is because we have checked for its uploaded files and have been expired.
In this case we need to trigger the build job again.

How does mozci deal with running/pending jobs?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mozci expects that running/pending _build_ jobs will trigger the tests we want.

If we want more than one job and we observe one running/pending job, we will
trigger as many jobs as needed to meet the request.

How does mozci deal with failed jobs?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mozci is not currently desgined to trigger jobs until they succeed.
The use must say what it wants to trigger and we will only do a one pass
to trigger everything requested.
This is purposeful for simplicity and to prevent triggering jobs endlessly.

In the near future, we will add a monitoring module which could be used
to keep track of triggered jobs and determine actions upon completion.

Can we schedule a PGO job on any tree?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Yes and no.
We can't trigger anything that the Release Engineering's Buildbot CI can trigger.
If a tree does not have a builder that generates a PGO build then we can't.

Notice that some trees can trigger both non-PGO jobs and PGO jobs, hence, that tree
has two different buildernames (one including "pgo" in its name).
Other trees can only trigger PGO jobs and might not include "pgo" in its name (think of
mozilla-aurora).

Can I trigger a nightly build?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Absolutely! Simply find the name of the job that represents it.

If I ask for different test jobs on the same changesets will I get as many builds jobs?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
There is a possible 30 seconds delay between making a request to buildapi and it appearing as "pending/running".
If you hit this issue please let us know and we can discuss it on how to better address it.
There are various options we can consider.

Does this work with TaskCluster?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Not yet.

What systems does mozci rely on?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you look at mozci.sources you will see all CI components we depend on.
If any of these changes, we might need to adjust mozci for it.

What happens if a new platform or suites are added to the CI?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Nothing to worry about! mozci determines platforms dynamically rather than statically.

What use cases are you hoping to address?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Please refer to :doc:`use_cases`.

I see that you store my credentials in plain text on my machine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you want a different approach please let us know.

Can I run mozci in my web service?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Yes! However, we will need to figure out how to provide credentials. More to come.

The Try server uses the try syntax; is that a problem?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No. We hit an API that is not affected by the try parser.
We can trigger whatever can be trigger without any limitations.

Can you trigger jobs on pushes with DONTBUILD?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No, we can not. This is a bug in buildapi. The pushes doesn't even exist for buildapi.
You can notice this if you load self-serve/buildapi for a DONTBUILD push.

How do you deal with coalesced and not scheduled jobs?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Coalesced jobs are requests that have been fulfilled by more recent pushes.
We coalesce jobs to be able to catch up under high load.

We sometimes not schedule jobs for various reasons including:

* The user has marked the job not to be built with DONTBUILD in the commit message
* The files changed on that push do not affect certain products/platforms
* We have determined that we don't need to trigger that job on every push

self-serve/buildapi does not keep track of jobs that have been coalesced or not scheduled.

mozci determines how many jobs to trigger a job depending on how many successful,
running jobs and potenrial jobs trigger by a build. Coalesced and not scheduled jobs are
not considered.

How do you release software?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We use zest.releaser. You simply install it: ::

    pip install zest.releaser

TBD - https://github.com/armenzg/mozilla_ci_tools/issues/29

How do I generate the docs?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To generate the docs, follow these steps:

* Move inside docs/ directory
* Run:
::

    pip install -r requirements.txt
    make html

* To view the docs on a webserver http://127.0.0.1:8000 and auto-rebuild
  the documentation when any files are changed:
::

    make livehtml

How can I contribute?
^^^^^^^^^^^^^^^^^^^^^

If you would like to contribute to this project, feel free to pick up one of the issues or tasks
in the Trello board (Tasks_) or the issues page (Issues_).

In order to contribute the code:

* Fork the project
* Create a new branch
* Fix the issue - add the feature
* Run tox successfully
* Commit your code
* Request a pull request

.. _Tasks: https://trello.com/b/BplNxd94/mozilla-ci-tools-public
.. _Pypi: https://pypi.python.org/pypi/mozci
.. _Issues: https://github.com/armenzg/mozilla_ci_tools/issues
