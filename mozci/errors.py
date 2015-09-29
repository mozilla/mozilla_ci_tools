#! /usr/bin/env python
"""This module holds custom-named exceptions"""


class AuthenticationError(Exception):
    pass


class BuildapiError(Exception):
    pass


class BuildjsonError(Exception):
    pass


class MozciError(Exception):
    pass


class TaskClusterError(Exception):
    pass


class TreeherderError(Exception):
    pass


class PushlogError(Exception):
    pass
