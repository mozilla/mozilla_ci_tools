#! /usr/bin/env python
"""This module holds custom-named exceptions"""


class MozciError(Exception):
    pass


class TreeherderError(Exception):
    pass


class BuildapiError(Exception):
    pass


class BuildjsonError(Exception):
    pass


class PushlogError(Exception):
    pass


class AuthenticationError(Exception):
    pass
