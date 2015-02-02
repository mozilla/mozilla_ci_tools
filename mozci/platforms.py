#! /usr/bin/env python
"""
This module helps us connect builds to tests since we don't have an API
to help us with this task.
"""
import logging

LOG = logging.getLogger()

# XXX: Once we have unit tests for this feature we will probably find
# issues, specially, in the b2g naming
PREFIX = {
    "Ubuntu VM 12.04": "Linux",
    "Ubuntu HW 12.04": "Linux",
    "Ubuntu VM 12.04 x64": "Linux x86-64",
    "Ubuntu HW 12.04 x64": "Linux x86-64",
    "Rev4 MacOSX Snow Leopard 10.6": "OS X 10.7",
    "Rev5 MacOSX Mountain Lion 10.8": "OS X 10.7",
    "Windows XP 32-bit": "WINNT 5.2",
    "Windows 7 32-bit": "WINNT 5.2",
    "Windows 8 64-bit": "WINNT 6.1 x86-64",
    "Android armv7 API 9": "Android armv7 API 9",
    "Android 4.0 armv7 API 11+": "Android armv7 API 11+",
    "Android 4.2 x86 Emulator": "Android 4.2 x86",
    "b2g_ubuntu32_vm": "b2g_%(repo_name)s_linux32_gecko",
    "b2g_ubuntu64_vm": "b2g_%(repo_name)s_linux64_gecko",
    "b2g_macosx64": "b2g_%(repo_name)s_macosx64_gecko",
    "b2g_emulator_vm": "b2g_%(repo_name)s_emulator",
}

JOB_TYPE = {
    "opt": "build",
    "pgo": "pgo-build",
    "debug": "leak test build",
    "talos": "build",
    "emulator": {
        "opt": "_dep",
        "debug": "-debug_dep",
    },
    "gecko": {
        "opt": " build",
    }
}


def associated_build_job(buildername, repo_name):
    '''
    The prefix and the post fix of a builder name can tell us
    the type of build job that triggered it.
    e.g. Windows 8 64-bit cedar opt test mochitest-1
    e.g. b2g_ubuntu64_vm cedar opt test gaia-unit

    We would prefer to have a non-mapping approach, however,
    we have not figured out an approach to determine the graph
    of dependencies.
    '''
    # XXX: This function does not work for build jobs as we
    #      don't have an easy way to determine if jobs are a
    #      test/talos job or a build one
    if buildername.find("b2g") == -1:
        prefix, job_type = buildername.split(" %s " % repo_name)
        job_type = job_type.split(" ")[0]
        associated_build = \
            "%s %s %s" % (PREFIX[prefix], repo_name, JOB_TYPE[job_type])
        LOG.debug("The build job that triggers %s is %s" % (buildername,
                                                            associated_build))
    else:
        prefix, job_type = buildername.split(" %s " % repo_name)
        job_type = job_type.split(" ")[0]
        build = PREFIX[prefix] % {"repo_name": repo_name}
        b2g_platform = build.split("_")[-1]
        postfix = JOB_TYPE[b2g_platform][job_type]
        associated_build = "%s%s" % (build, postfix)
        LOG.debug("The build job that triggers %s is %s" % (buildername,
                                                            associated_build))
    return associated_build


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
