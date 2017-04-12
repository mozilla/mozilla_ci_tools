#! /usr/bin/env python
"""This module holds custom-named exceptions"""


class AuthenticationError(Exception):
    pass


class BuildapiError(Exception):
    pass


class BuildjsonError(Exception):
    pass


class MissingBuilderError(Exception):
    pass


class MozciError(Exception):
    pass


class PushlogError(Exception):
    pass


class TaskClusterArtifactError(Exception):
    pass


class TaskClusterError(Exception):
    pass


class TreeherderError(Exception):
    pass
