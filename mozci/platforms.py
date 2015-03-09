#! /usr/bin/env python
"""This module helps us connect builds to tests."""
import collections
import logging

from sources.allthethings import fetch_allthethings_data

LOG = logging.getLogger()
# We will start by pre-computing some structures that will be used for
# determine_upstream_builder. They are globals so we don't compute them over
# and over again when calling determine_upstream_builder multiple times

all_builders_information = fetch_allthethings_data()
buildernames = all_builders_information['builders'].keys()


def is_downstream(buildername):
    """Determine if a job requires files to be triggered."""
    props = all_builders_information['builders'][buildername]['properties']
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
shortname_to_name = {}

# For every test job we can find the scheduler that runs it and the
# corresponding trigger in allthethings.json. For example:
# "schedulers": {...
# "tests-larch-panda_android-opt-unittest": {
#    "downstream": [ "Android 4.0 armv7 API 11+ larch opt test cppunit", ...],
#    "triggered_by": ["larch-android-api-11-opt-unittest"]},
# means that "Android 4.0 armv7 API 11+ larch opt test cppunit" is ran
# by the "tests-larch-panda_android-opt-unittest" scheduler, and this
# scheduler is triggered by "larch-android-api-11-opt-unittest". In
# buildername_to_trigger we'll store the corresponding trigger to
# every test job. In this case, "Android 4.0 armv7 API 11+ larch opt
# test cppunit" : larch-android-api-11-opt-unittest
buildername_to_trigger = {}

# We'll look at every builder and if it's a build job we will add it
# to shortname_to_name
build_jobs = []
for buildername in buildernames:
    # Skipping nightly for now
    if 'nightly' in buildername:
        continue

    builder_info = all_builders_information['builders'][buildername]
    props = builder_info['properties']
    # We heuristically figure out what jobs are build jobs by checking
    # the "slavebuilddir" property
    if not is_downstream(buildername):
        shortname_to_name[builder_info['shortname']] = buildername
        build_jobs.append(buildername)

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
for sched, values in all_builders_information['schedulers'].iteritems():
    # We are only interested in test schedulers
    if not sched.startswith('tests-'):
        continue

    for buildername in values['downstream']:
        assert buildername not in buildername_to_trigger
        buildername_to_trigger[buildername.lower()] = values['triggered_by'][0]


def determine_upstream_builder(buildername):
    """
    Given a builder name, find the build job that triggered it.

    When buildername corresponds to a test job it determines the
    triggering build job through allthethings.json. When a buildername
    corresponds to a build job, it returns it unchanged.
    """
    # If a buildername is in build_jobs, it means that it's a build job
    # and it should be returned unchanged
    for build_job in build_jobs:
        if build_job.lower() == buildername.lower():
            return build_job

    # For some (but not all) platforms and repos, -pgo is explicit in
    # the trigger but not in the shortname, e.g. "Linux
    # mozilla-release build" shortname is "mozilla-release-linux" but
    # the associated trigger name is
    # "mozilla-release-linux-pgo-unittest"
    SUFFIXES = ['-opt-unittest', '-unittest', '-talos', '-pgo']

    # Guess the build job's shortname from the test job's trigger
    # e.g. from "larch-android-api-11-opt-unittest"
    # look for "larch-android-api-11" in shortname_to_name and find
    # "Android armv7 API 11+ larch build"
    if buildername.lower() not in buildername_to_trigger:
        LOG.error("We didn't find a build job matching %s" % buildername)
        raise Exception("No build job found.")

    shortname = buildername_to_trigger[buildername.lower()]
    for suffix in SUFFIXES:
        if shortname.endswith(suffix):
            shortname = shortname[:-len(suffix)]
            if shortname in shortname_to_name:
                return shortname_to_name[shortname]

    # B2G jobs are weird
    shortname = "b2g_" + shortname.replace('-emulator', '_emulator') + "_dep"
    if shortname in shortname_to_name:
        return shortname_to_name[shortname]


def get_associated_platform_name(buildername):
    """Given a buildername, find the platform in which it is ran."""
    props = all_builders_information['builders'][buildername]['properties']
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
