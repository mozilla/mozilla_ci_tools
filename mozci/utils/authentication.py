# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

"""Module for http authentication operations."""

import getpass
import keyring
import logging
import os

CREDENTIALS_PATH = os.path.expanduser("~/.mozilla/credentials.cfg")
DIRNAME = os.path.dirname(CREDENTIALS_PATH)
LOG = logging.getLogger('mozci')
AUTH = None


class AuthenticationError(Exception):
    pass


def get_credentials():
    """
    Return credentials for http access either from disk or directly
    from the user (which we store).
    """
    global AUTH
    if AUTH is not None:
        return AUTH

    if 'LDAP_USER' in os.environ.keys() and 'LDAP_PW' in os.environ.keys():
        AUTH = (os.environ['LDAP_USER'], os.environ['LDAP_PW'])
        return AUTH

    if not os.path.exists(DIRNAME):
        os.makedirs(DIRNAME)

    content = None
    if os.path.isfile(CREDENTIALS_PATH):
        with open(CREDENTIALS_PATH, 'r') as file_handler:
            content = file_handler.read().splitlines()

        if len(content) != 1:
            # This is a temporary block until we remove all plain-text
            # stored passwords.
            remove_credentials()
            LOG.debug("We used to store passwords in plain-text."
                      "We are sorry this was done and we're removing the file"
                      "The new format *only* allows for encrypted; only if"
                      "desired.")

    if content is not None:
        LOG.debug("Loading LDAP user from %s" % CREDENTIALS_PATH)
        https_username = content[0].strip()
        https_password = keyring.get_password("mozci", https_username)
        if https_password is None or https_password == "":
            https_password = getpass.getpass(
                "Input LDAP password for user %s: " % https_username)
    else:
        https_username = raw_input(
            "Please enter your full LDAP email address: ")
        https_password = getpass.getpass()
        store_password = raw_input(
            "Do you want to store your password in encrypted form (y or n)? ")

        with open(CREDENTIALS_PATH, "w+") as file_handler:
            file_handler.write("%s\n" % https_username)

        if store_password == "y":
            keyring.set_password("mozci", https_username, https_password)
        else:
            keyring.set_password("mozci", https_username, "")

        os.chmod(CREDENTIALS_PATH, 0600)
        LOG.info("The LDAP username will be stored in %s" % CREDENTIALS_PATH)

    AUTH = (https_username, https_password)
    return AUTH


def remove_credentials():
    """Removes the file stored at CREDENTIALS_PATH"""
    os.remove(CREDENTIALS_PATH)


def get_credentials_path():
    """Return path to file containing credentials."""
    if os.path.isfile(CREDENTIALS_PATH):
        get_credentials()

    return CREDENTIALS_PATH
