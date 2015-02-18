#! /usr/bin/env python
"""
This module helps us connect builds to tests since we don't have an API
to help us with this task.
"""
import sources.allthethings

import logging

LOG = logging.getLogger()

data = sources.allthethings._fetch_json()
builders = sources.allthethings.list_builders()

shortname_to_name = {}
buildername_to_trigger = {}

for build in builders:
    # Skipping these for now
    if 'nightly' in build:
        continue

    builder = data['builders'][build]
    props = builder['properties']
    # We will later associate test job names to the name of the build job
    # that created them. In order to do this, we heuristically figure out
    # what jobs are build jobs by checking the "slavebuilddir" property
    if 'slavebuilddir' not in props or props['slavebuilddir'] != 'test':
        shortname_to_name[builder['shortname']] = build

for sched, values in data['schedulers'].iteritems():
    if not sched.startswith('tests-'):
        continue

    for builder in values['downstream']:
        assert builder not in buildername_to_trigger
        buildername_to_trigger[builder] = values['triggered_by'][0]


def associated_build_job(buildername, repo_name):
    '''Given a builder name, find the build job that triggered it. When
    buildername corresponds to a test job, it does so by looking at
    allthethings.json. When buildername corresponds to a build job, it
    passes through unchanged.
    '''
    assert repo_name in buildername, \
        "You have requested '%s' buildername, " % buildername + \
        "however, the key '%s' " % repo_name + \
        "is not found in it."

    # For some (but not all) platforms and repos, -pgo is explicit in
    # the trigger but not in the shortname
    SUFFIXES = ['-opt-unittest', '-unittest', '-talos', '-pgo']

    if buildername not in buildername_to_trigger:
        return buildername

    # Guess the build job's shortname from the test job's trigger
    shortname = buildername_to_trigger[buildername]
    for suffix in SUFFIXES:
        if shortname.endswith(suffix):
            shortname = shortname[:-len(suffix)]
            if shortname in shortname_to_name:
                return shortname_to_name[shortname]

    # B2G jobs are weird
    shortname = "b2g_" + shortname.replace('-emulator', '_emulator') + "_dep"
    if shortname in shortname_to_name:
        return shortname_to_name[shortname]


def does_builder_need_files(buildername):
    ''' Determine if a job requires files to be triggered.
    '''
    # XXX: This is closely tied to the buildbot naming
    # We could determine this by looking if the builder belongs to
    # the right schedulers in allthethings.json
    for match in ("opt", "pgo", "debug", "talos"):
        if buildername.find(match) != -1:
            return True
    return False
