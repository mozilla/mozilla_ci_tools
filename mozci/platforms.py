#! /usr/bin/env python
"""This module helps us connect builds to tests."""
from __future__ import absolute_import

import collections
import logging
import os
import re

from mozci.errors import MozciError
from mozci.sources.allthethings import fetch_allthethings_data

LOG = logging.getLogger('mozci')

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
UPSTREAM_TO_DOWNSTREAM = None
SETA_DICT = None
MAX_PUSHES = 5


def is_upstream(buildername):
    """Determine if a job triggered by any other."""
    return not is_downstream(buildername)


def is_downstream(buildername):
    """Determine if a job requires a build job to have triggered."""
    return get_buildername_metadata(buildername)['downstream']


def _process_data():
    """Filling the dictionaries used by determine_upstream_builder."""
    # We check if we already computed before
    if BUILDERNAME_TO_TRIGGER:
        return

    LOG.debug("Computing builders' relations from allthethings data.")
    # We'll look at every builder and if it's a build job we will add it
    # to SHORTNAME_TO_NAME
    for buildername, builderinfo in fetch_allthethings_data()['builders'].iteritems():
        if not _wanted_builder(buildername):
            continue

        if is_upstream(buildername):
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


def get_SETA_interval_dict(force=False):
    """
    Return dictionary with SETA intervals for buildernames.

    SETA intervals are in the form of [7, 3600] where 7 represents the number of pushes after
    SETA runs and 3600 represents time interval in seconds after which SETA runs
    if number of pushes isn't reached.

    :param force: Default False. Forces refresh of SETA dict.
    :type force: boolean
    :returns: Returns dict with buildernames as keys and SETA interval as value.
    :rtype: dict

    """
    global SETA_DICT

    if SETA_DICT and not force:
        return SETA_DICT

    SETA_DICT = {}
    for sched, values in fetch_allthethings_data()['schedulers'].iteritems():
        # We are only interested in test schedulers
        # Example scheduler names:
        # tests-fx-team-snowleopard-debug-unittest-7-3600
        # tests-fx-team-snowleopard-opt-unittest-7-3600
        if not sched.startswith('tests-'):
            continue

        sched_str_list = sched.split('-')
        # Only schedulers with SETA information have a numeric value
        # [u'tests', u'fx', u'team', u'snowleopard', u'opt', u'unittest', u'7', u'3600']
        # [u'tests', u'fx', u'team', u'ubuntu64_vm', u'opt', u'unittest']
        # We can call isnumeric because it is a unicode value
        if sched_str_list[-1].isnumeric():
            pushes = int(sched_str_list[-2])
            seconds = int(sched_str_list[-1])
            # Iterate over all the downstream builders this scheduler schedules
            for buildername in values['downstream']:
                SETA_DICT[buildername] = [pushes, seconds]

    return SETA_DICT


def get_SETA_info(buildername):
    if not SETA_DICT:
        get_SETA_interval_dict()

    return SETA_DICT.get(buildername, None)


def get_max_pushes(buildername):
    ''' Determine the maximum number of pushes we can go by without scheduling this builder.

    If a buildername is affected by SETA return the number of pushes we can go by without
    scheduling such job.

    If not, use the MAX_PUSHES default.

    '''
    seta_info = get_SETA_info(buildername)

    if seta_info is None:
        max_pushes = MAX_PUSHES
    else:
        max_pushes = seta_info[0]

    return max_pushes


def determine_upstream_builder(buildername):
    """
    Given a builder name, find the build job that triggered it.

    When buildername corresponds to a test job it determines the
    triggering build job through allthethings.json. When a buildername
    corresponds to a build job, it returns it unchanged.

    Raises MozciError if no matching build job is found.
    """
    _process_data()

    # For some platforms in mozilla-beta and mozilla-aurora there are both
    # talos and pgo talos jobs, only the pgo talos ones are valid.
    if 'mozilla-beta' in buildername or 'mozilla-aurora' in buildername:
        if 'talos' in buildername and 'pgo' not in buildername:
            buildername_with_pgo = buildername.replace('talos', 'pgo talos')
            if buildername_with_pgo.lower() in BUILDERNAME_TO_TRIGGER:
                # The non pgo talos builders don't have a parent to trigger them
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
        raise MozciError("No build job matching %s found." % buildername)

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


def _get_raw_builder_metadata(buildername):
    """Return all metadata from allthethings associated to a builder."""
    return fetch_allthethings_data()['builders'][buildername]


def _get_repo_name(repo_path):
    """Return the repository name of the given repository path."""
    return os.path.basename(repo_path) if '/' in repo_path else repo_path


def get_buildername_metadata(buildername):
    """Return metadata associated to a buildername.

    Returns a dictionary with the following information:
        * build_type - It returns 'opt' or 'debug' or 'pgo'
        * downstream - If the job requires an upstream job to be triggered
        * job_type - It returns 'build', 'test' or 'talos'
        * platform_name - It associates upstream & downstream builders (e.g. win32)
        * product - e.g. firefox
        * repo_name - Associated short name for a repository (e.g. alder)
        * suite_name - talos & test jobs have an associated suite name (e.g chromez)
    """
    if buildername not in fetch_allthethings_data()['builders']:
        raise MozciError("Builder '{}' is missing. All builders' lenght: {}".format(
            buildername, len(fetch_allthethings_data()['builders']))
        )

    props = _get_raw_builder_metadata(buildername)['properties']

    meta = {
        'downstream': 'slavebuilddir' in props and props['slavebuilddir'] == 'test',
        'platform_name': props['platform'],
        'product': props['product'],
        'repo_name': _get_repo_name(props.get('branch')),
    }

    # Build jobs
    if not meta['downstream']:
        meta['job_type'] = 'build'
        suite_name = None

    else:
        # e.g. 'Windows 7 32-bit mozilla-central pgo talos chromez-e10s' -> chromez-e10s
        suite_name = str(buildername.split(" ")[-1])

        # Talos jobs
        if 'talos' in buildername:
            meta['job_type'] = 'talos'
            # For talos tests we have to check stage_platform instead of platform
            meta['platform_name'] = props['stage_platform']

        # Test jobs
        elif 'test' in buildername:
            meta['job_type'] = 'test'

    ending = meta['platform_name'].split('-')[-1]
    if ending in ('debug', 'opt', 'pgo'):
        # e.g. win32-st-an-debug, emulator-debug, win32-debug
        # build_type == 'debug'
        # platform_name == ('win32-st-an', 'emulator', 'win32')
        meta['build_type'] = ending
        meta['platform_name'] = meta['platform_name'][:-len(ending) - 1]
    elif 'debug' in buildername:
        meta['build_type'] = 'debug'
    elif 'opt' in buildername:
        meta['build_type'] = 'opt'
    elif 'pgo' in buildername:
        meta['build_type'] = 'pgo'
    elif meta['job_type'] == 'build':
        # Release repositories *only* have PGO builds even though their name does not contain
        # 'pgo' in the buildername
        if meta['repo_name'] in ('mozilla-aurora', 'mozilla-beta', 'mozilla-release', 'esr'):
            meta['build_type'] = 'pgo'
        else:
            meta['build_type'] = 'opt'
    else:
        # e.g. Rev7 MacOSX Yosemite 10.10.5 mozilla-beta talos other-e10s
        meta['build_type'] = 'opt'

    assert all(meta)
    # Since builds don't have a suite name
    meta['suite_name'] = suite_name

    return meta


def get_associated_platform_name(buildername):
    return get_buildername_metadata(buildername)['platform_name']


def _get_job_type(test_job):
    """
    Classify a job as 'opt', 'debug' or 'pgo' based on its name.

    Currently only working for test jobs with buildbot's desktop and
    mobile jobs naming. This function does not apply to B2g and
    TaskCluster.
    """
    return get_buildername_metadata(test_job)['build_type']


def build_tests_per_platform_graph(builders):
    """Return a graph mapping platforms to tests that run in it."""
    graph = {'debug': {}, 'opt': {}, 'pgo': {}}
    up_builders = []
    dn_builders = []

    # Let's separate upstream from downstream builders
    for builder in builders:
        # Ignore invalid builders
        if not _wanted_builder(builder):
            continue

        if is_upstream(builder):
            up_builders.append(builder)
        else:
            dn_builders.append(builder)

    # Let's start building the graph with the upstream builders
    for upstream_builder in up_builders:
        # Each builder has a platform name associated to them
        # e.g. WINNT 5.2 {{branch}} build --> win32
        # e.g. WINNT 5.2 {{branch}} leak test build --> win32-debug
        info = get_buildername_metadata(upstream_builder)
        build_type = info['build_type']
        platform_name = info['platform_name']

        if platform_name not in graph[build_type]:
            graph[build_type][platform_name] = collections.defaultdict(list)
            graph[build_type][platform_name]['tests'] = []

        graph[build_type][platform_name][upstream_builder] = []

    # Let's add the downstream builders to the graph of upstream builders
    for downstream_builder in dn_builders:
        upstream_builder = determine_upstream_builder(downstream_builder)
        # Parental info
        info = get_buildername_metadata(upstream_builder)
        build_type = info['build_type']
        platform_name = info['platform_name']
        # Suite name from the downstream builder
        dn_builder_info = get_buildername_metadata(downstream_builder)
        suite_name = dn_builder_info['suite_name']

        # Some builders in allthethings (for example, "Ubuntu Code
        # Coverage VM 12.04 x64 try debug test cppunit") are not
        # triggered by any upstream builders and we must skip them
        if upstream_builder is None:
            continue

        # We need to add test jobs to their corresponding upstream
        # builders key and test types to the list of tests that ran in
        # that platform.
        if suite_name not in graph[build_type][platform_name]['tests']:
            # XXX: under 'tests' we're pilling up all suites from each
            # associated builder to that platform_name. Fix this in next pass
            graph[build_type][platform_name]['tests'].append(suite_name)

        graph[build_type][platform_name][upstream_builder].append(downstream_builder)

    # Let's sort all the suite names
    for build_type in graph:
        for platform_name in graph[build_type]:
            for t in graph[build_type][platform_name]:
                graph[build_type][platform_name][t].sort()

    return graph


def get_talos_jobs_for_build(buildername):
    buildernames = []
    build_type = 'pgo' if get_buildername_metadata(buildername)['build_type'] == 'pgo' else 'opt'
    downstream_jobs = get_downstream_jobs(buildername)
    for job in downstream_jobs:
        info = get_buildername_metadata(job)
        if info['build_type'] == build_type and info['job_type'] == 'talos':
            buildernames.append(job)
    return buildernames


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
    buildernames = list_builders()
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
        # This is a temporary hack to not trigger 'Windows 10' jobs on try.
        # Remove it when not necessary.
        if 'Windows 10' in builder:
            continue
        retVal.append(builder)

    retVal.sort()
    return retVal


def _include_builders_matching(builders, keyword):
    """Find all the builders in a list that contain a keyword."""
    return map(str, filter(lambda x: keyword in x, builders))


def _exclude_builders_matching(builders, keyword):
    """Find all the builders in a list that contain a keyword."""
    return map(str, filter(lambda x: keyword not in x, builders))


def find_buildernames(repo, suite_name=None, platform=None, job_type='opt'):
    """
    Return a list of buildernames matching the criteria.

    1) if the developer provides suite_name, repo and platform and job_type
    return only the specific buildername
    2) if the developer provides suite_name and platform only, then return
    the suite_name for all platforms
    3) if the developer provides platform and repo, then return all
    the suite_name for that platform
    """
    assert suite_name is not None or platform is not None, \
        'suite_name and platform cannot both be None.'

    buildernames = list_builders(repo)

    if suite_name is not None:
        buildernames = filter(
            lambda x:
            get_buildername_metadata(x)['suite_name'] == suite_name,
            buildernames)
    # If no specific suite has been chosen we should then select all tests jobs
    else:
        buildernames = filter(lambda x: is_downstream(x), buildernames)

    if platform is not None:
        buildernames = filter(lambda x:
                              get_associated_platform_name(x) == platform,
                              buildernames)

    if job_type is not None:
        buildernames = filter(lambda x: _get_job_type(x) == job_type, buildernames)

    return buildernames


def filter_buildernames(buildernames, include=[], exclude=[]):
    """Return every builder matching the words in include and not in exclude."""

    for word in include:
        buildernames = filter(lambda x: word.lower() in x.lower(), buildernames)

    for word in exclude:
        buildernames = filter(lambda x: word.lower() not in x.lower(), buildernames)

    return sorted(buildernames)


def _wanted_builder(builder, filter=True):
    """ Filter unnecessary builders that Buildbot's setup has.

    If you call the function without filter is the same as always returning True.
    """
    if not filter:
        # XXX: revisit why we allow for this option
        return True
    else:
        # We lack metadata in allthethings for release builders
        # in order to call get_buildername_metadata()
        # We don't care about the hg bundle builders
        if builder.startswith('release-') or \
           builder.endswith('bundle'):
            return False

        info = get_buildername_metadata(builder)

        # On aurora and beta we have pgo and opt builders for talos even though
        # there is no build to trigger the pgo builders. Exclude those builders as valid
        # This is to work around bug 1149514
        if info['repo_name'] in ('mozilla-aurora', 'mozilla-beta') and \
           info['job_type'] == 'talos':
            equiv_pgo_builder = builder.replace('talos', 'pgo talos')
            if equiv_pgo_builder in fetch_allthethings_data()['builders']:
                # There are two talos builders, we only can use the pgo one
                return False

    return True


def list_builders(repo_name=None, filter=True):
    """Return a list of all builders running in the buildbot CI."""
    all_builders = fetch_allthethings_data()['builders']
    assert len(all_builders) > 0, "The list of builders cannot be empty."

    # Let's filter out builders which are not triggered per push
    # and are not associated to a repo_name if set
    builders_list = []
    for builder in all_builders.keys():
        if repo_name and repo_name not in builder:
            continue
        if _wanted_builder(builder=builder, filter=filter):
            builders_list.append(builder)

    return builders_list


def _generate_builders_relations_dictionary():
    """Create a dictionary that maps every upstream job to its downstream jobs."""
    builders = list_builders()
    relations = collections.defaultdict(list)
    for buildername in builders:
        if is_downstream(buildername):
            relations[determine_upstream_builder(buildername)].append(buildername)
    return relations


def load_relations():
    """Loads upstream to downstream mapping."""
    global UPSTREAM_TO_DOWNSTREAM
    if UPSTREAM_TO_DOWNSTREAM is None:
        UPSTREAM_TO_DOWNSTREAM = _generate_builders_relations_dictionary()


def get_downstream_jobs(upstream_job):
    """Return all test jobs that are downstream from a build job."""
    load_relations()
    return UPSTREAM_TO_DOWNSTREAM[upstream_job]
