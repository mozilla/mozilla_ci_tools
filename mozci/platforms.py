#! /usr/bin/env python
"""This module helps us connect builds to tests."""
import collections
import logging

from sources.allthethings import fetch_allthethings_data

LOG = logging.getLogger()


def is_downstream(buildername):
    """Determine if a job requires files to be triggered."""
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
        # Skipping nightly for now
        if 'nightly' in buildername:
            continue

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
    # If a buildername is in BUILD_JOBS, it means that it's a build job
    # and it should be returned unchanged
    if buildername.lower() in BUILD_JOBS:
        return BUILD_JOBS[buildername.lower()]

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
                return SHORTNAME_TO_NAME[shortname]

    # B2G jobs are weird
    shortname = "b2g_" + shortname.replace('-emulator', '_emulator') + "_dep"
    if shortname in SHORTNAME_TO_NAME:
        return SHORTNAME_TO_NAME[shortname]


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


def build_tests_per_platform_graph(builders):
    """Return a graph mapping platforms to tests that run in it."""
    graph = collections.defaultdict(list)

    for builder in builders:
        if is_downstream(builder):
            platform = get_associated_platform_name(builder)
            test = _get_test(builder)
            if test not in graph[platform]:
                graph[platform].append(test)

    for platform in graph:
        graph[platform].sort()

    return graph
