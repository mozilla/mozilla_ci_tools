#! /usr/bin/env python
"""This module helps us connect builds to tests."""
import collections
import logging
import re

from sources.allthethings import fetch_allthethings_data

LOG = logging.getLogger()


def is_downstream(buildername):
    """Determine if a job requires files to be triggered."""
    # Builders in gaia-try are at same time build and test jobs, and
    # should be considered upstream.
    if " gaia-try " in buildername:
        return False

    props = fetch_allthethings_data()['builders'][buildername]['properties']
    return 'slavebuilddir' in props and props['slavebuilddir'] == 'test'

# In buildbot, once a build job finishes, it triggers a scheduler,
# which causes several tests to run. In allthethings.json we have the
# name of the trigger that activates a scheduler, but what each build
# job triggers is not directly available from the json file. Since
# trigger names for a given build are similar to their shortnames,
# which are available in allthethings.json, we'll use shortnames to
# find the which builder triggered a given scheduler given only the
# trigger name. In order to do that we'll need a mapping from
# shortnames to build jobs. For example:
# "Android armv7 API 11+ larch build":
#               { ...  "shortname": "larch-android-api-11", ...},
# Will give us the entry:
# "larch-android-api-11" : "Android armv7 API 11+ larch build"
SHORTNAME_TO_NAME = {}

# For every test job we can find the scheduler that runs it and the
# corresponding trigger in allthethings.json. For example:
# "schedulers": {...
# "tests-larch-panda_android-opt-unittest": {
#    "downstream": [ "Android 4.0 armv7 API 11+ larch opt test cppunit", ...],
#    "triggered_by": ["larch-android-api-11-opt-unittest"]},
# means that "Android 4.0 armv7 API 11+ larch opt test cppunit" is ran
# by the "tests-larch-panda_android-opt-unittest" scheduler, and this
# scheduler is triggered by "larch-android-api-11-opt-unittest". In
# BUILDERNAME_TO_TRIGGER we'll store the corresponding trigger to
# every test job. In this case, "Android 4.0 armv7 API 11+ larch opt
# test cppunit" : larch-android-api-11-opt-unittest
BUILDERNAME_TO_TRIGGER = {}
BUILD_JOBS = {}


def _process_data():
    """Filling the dictionaries used by determine_upstream_builder."""
    # We check if we already computed before
    if BUILDERNAME_TO_TRIGGER:
        LOG.debug("Reusing builders' relations computed from allthethings data.")
        return

    LOG.debug("Computing builders' relations from allthethings data.")
    # We'll look at every builder and if it's a build job we will add it
    # to SHORTNAME_TO_NAME
    for buildername, builderinfo in fetch_allthethings_data()['builders'].iteritems():
        if not is_downstream(buildername):
            SHORTNAME_TO_NAME[builderinfo['shortname']] = buildername
            BUILD_JOBS[buildername.lower()] = buildername

    # data['schedulers'] is a dictionary that maps a scheduler name to a
    # dictionary of it's properties:
    # "schedulers": {...
    # "tests-larch-panda_android-opt-unittest": {
    #    "downstream": [ "Android 4.0 armv7 API 11+ larch opt test cppunit",
    #                    "Android 4.0 armv7 API 11+ larch opt test crashtest",
    #                    "Android 4.0 armv7 API 11+ larch opt test jsreftest-1",
    #                    "Android 4.0 armv7 API 11+ larch opt test jsreftest-2",
    #                    ... ],
    #    "triggered_by": ["larch-android-api-11-opt-unittest"]},
    # A test scheduler has a list of tests in "downstream" and a trigger
    # name in "triggered_by". We will map every test in downstream to the
    # trigger name in triggered_by
    for sched, values in fetch_allthethings_data()['schedulers'].iteritems():
        # We are only interested in test schedulers
        if not sched.startswith('tests-'):
            continue

        for buildername in values['downstream']:
            assert buildername.lower() not in BUILDERNAME_TO_TRIGGER
            BUILDERNAME_TO_TRIGGER[buildername.lower()] = values['triggered_by'][0]


def determine_upstream_builder(buildername):
    """
    Given a builder name, find the build job that triggered it.

    When buildername corresponds to a test job it determines the
    triggering build job through allthethings.json. When a buildername
    corresponds to a build job, it returns it unchanged.
    """
    _process_data()

    # For some platforms in mozilla-beta and mozilla-aurora there are both
    # talos and pgo talos jobs, only the pgo talos ones are valid.
    if 'mozilla-beta' in buildername or 'mozilla-aurora' in buildername:
        if 'talos' in buildername and 'pgo' not in buildername:
            buildername_with_pgo = buildername.replace('talos', 'pgo talos')
            if buildername_with_pgo.lower() in BUILDERNAME_TO_TRIGGER:
                return

    # If a buildername is in BUILD_JOBS, it means that it's a build job
    # and it should be returned unchanged
    if buildername.lower() in BUILD_JOBS:
        return str(BUILD_JOBS[buildername.lower()])

    # For some (but not all) platforms and repos, -pgo is explicit in
    # the trigger but not in the shortname, e.g. "Linux
    # mozilla-release build" shortname is "mozilla-release-linux" but
    # the associated trigger name is
    # "mozilla-release-linux-pgo-unittest"
    SUFFIXES = ['-opt-unittest', '-unittest', '-talos', '-pgo']

    # Guess the build job's shortname from the test job's trigger
    # e.g. from "larch-android-api-11-opt-unittest"
    # look for "larch-android-api-11" in SHORTNAME_TO_NAME and find
    # "Android armv7 API 11+ larch build"
    if buildername.lower() not in BUILDERNAME_TO_TRIGGER:
        LOG.error("We didn't find a build job matching %s" % buildername)
        raise Exception("No build job found.")

    shortname = BUILDERNAME_TO_TRIGGER[buildername.lower()]
    for suffix in SUFFIXES:
        if shortname.endswith(suffix):
            shortname = shortname[:-len(suffix)]
            if shortname in SHORTNAME_TO_NAME:
                return str(SHORTNAME_TO_NAME[shortname])

    # B2G jobs are weird
    shortname = "b2g_" + shortname.replace('-emulator', '_emulator') + "_dep"
    if shortname in SHORTNAME_TO_NAME:
        return str(SHORTNAME_TO_NAME[shortname])


def get_associated_platform_name(buildername):
    """Given a buildername, find the platform in which it is ran."""
    props = fetch_allthethings_data()['builders'][buildername]['properties']
    # For talos tests we have to check stage_platform
    if 'talos' in buildername:
        return props['stage_platform']
    else:
        return props['platform']


def _get_test(buildername):
    """
    For test jobs, the test type is the last part of the name.

    For example:
    in Windows 7 32-bit mozilla-central pgo talos chromez-e10s
    the test type is chromez-e10s
    """
    return buildername.split(" ")[-1]


def _get_job_type(test_job):
    """
    Classify a job as 'opt', 'debug' or 'pgo' based on its name.

    Currently only working for test jobs with buildbot's desktop and
    mobile jobs naming. This function does not apply to B2g and
    TaskCluster.
    """
    job_type = None

    if 'pgo test' in test_job or 'pgo talos' in test_job:
        job_type = 'pgo'
    elif 'opt' in test_job or 'talos' in test_job:
        job_type = 'opt'
    elif 'debug' in test_job:
        job_type = 'debug'
    return job_type


def _filter_builders_matching(builders, keyword):
    """Find all the builders in a list that contain a keyword."""
    return map(str, filter(lambda x: keyword in x, builders))


def build_tests_per_platform_graph(builders):
    """Return a graph mapping platforms to tests that run in it."""
    graph = {'debug': {}, 'opt': {}}

    for builder in builders:
        test = None
        if is_downstream(builder):
            upstream = determine_upstream_builder(builder)
            # Some builders in allthethings (for example, "Ubuntu Code
            # Coverage VM 12.04 x64 try debug test cppunit") are not
            # triggered by any upstream and we must skip them
            if upstream is None:
                continue

            platform = get_associated_platform_name(upstream)
            test = _get_test(builder)

        else:
            platform = get_associated_platform_name(builder)
            upstream = builder

        if platform.endswith('-debug'):
            key = 'debug'
            platform = platform[:-len('-debug')]

        else:
            key = 'opt'

        if platform not in graph[key]:
            graph[key][platform] = collections.defaultdict(list)
            graph[key][platform]['tests'] = []

        # We need to add test jobs to their corresponding upstream
        # builders key and test types to the list of tests that ran in
        # that platform.
        if test is not None:
            graph[key][platform][upstream].append(builder)

            if test not in graph[key][platform]['tests']:
                graph[key][platform]['tests'].append(test)

        # Even build jobs with no test jobs should be keys in the
        # graph.
        if upstream not in graph[key][platform]:
            graph[key][platform][upstream] = []

    for key in graph:
        for platform in graph[key]:
            for t in graph[key][platform]:
                graph[key][platform][t].sort()

    return graph


def build_talos_buildernames_for_repo(repo_name, pgo_only=False):
    """
    This function aims to generate all possible talos jobs for a given branch.

    Here we take the list of talos buildernames for a given branch.   When
    we want pgo, we build a list of pgo buildernames, then find the non-pgo builders
    which do not have a pgo equivalent.  To do this, we hack the buildernames in
    a temporary set by removing ' pgo' from the name, then finding the unique jobs
    in the talos_re jobs.  Now we can take the pgo jobs and jobs with no pgo
    equivalent and have a full set of pgo jobs.
    """
    buildernames = fetch_allthethings_data()['builders']
    retVal = []

    # Android and OSX do not have PGO, so we need to get those specific jobs
    pgo_re = re.compile(".*%s pgo talos.*" % repo_name)
    talos_re = re.compile(".*%s talos.*" % repo_name)

    talos_jobs = set()
    pgo_jobs = set()
    tp_jobs = set()
    for builder in buildernames:
        if talos_re.match(builder):
            talos_jobs.add(builder)

        if pgo_re.match(builder):
            pgo_jobs.add(builder)
            tp_jobs.add(builder.replace(' pgo', ''))

    if pgo_only:
        non_pgo_jobs = talos_jobs - tp_jobs
        talos_jobs = pgo_jobs.union(non_pgo_jobs)

    for builder in talos_jobs:
        retVal.append(builder)

    retVal.sort()
    return retVal


def find_buildernames(repo, test=None, platform=None, job_type='opt'):
    """
    Return a list of buildernames matching the criteria.

    1) if the developer provides test, repo and platform and job_type
    return only the specific buildername
    2) if the developer provides test and platform only, then return
    the test on all platforms
    3) if the developer provides platform and repo, then return all
    the tests on that platform
    """
    assert test is not None or platform is not None, 'test and platform cannot both be None.'

    buildernames = _filter_builders_matching(fetch_allthethings_data()['builders'].keys(),
                                             ' %s ' % repo)
    if test is not None:
        buildernames = _filter_builders_matching(buildernames, test)
    # Even when test is None we still only want test jobs
    else:
        buildernames = filter(lambda x: is_downstream(x), buildernames)

    if platform is not None:
        buildernames = filter(lambda x: get_associated_platform_name(x) == platform, buildernames)

    if job_type is not None:
        buildernames = filter(lambda x: _get_job_type(x) == job_type, buildernames)

    return buildernames
