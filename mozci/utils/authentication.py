# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

"""Module for http authentication operations."""

import getpass
import logging
import os

CREDENTIALS_PATH = os.path.expanduser("~/.mozilla/credentials.cfg")
DIRNAME = os.path.dirname(CREDENTIALS_PATH)
LOG = logging.getLogger('mozci')


def get_credentials():
    """
    Return credentials for http access either from disk or directly
    from the user (which we store).
    """
    if not os.path.exists(DIRNAME):
        os.makedirs(DIRNAME)

    if os.path.isfile(CREDENTIALS_PATH):
        with open(CREDENTIALS_PATH, 'r') as file_handler:
            content = file_handler.read().splitlines()

        LOG.debug("Loading LDAP credentials from %s" % CREDENTIALS_PATH)
        https_username = content[0].strip()
        https_password = content[1].strip()
    else:
        https_username = raw_input(
            "Please enter your full LDAP email address: ")
        https_password = getpass.getpass()

        with open(CREDENTIALS_PATH, "w+") as file_handler:
            file_handler.write("%s\n" % https_username)
            file_handler.write("%s\n" % https_password)

        os.chmod(CREDENTIALS_PATH, 0600)
        LOG.info("LDAP credentials will be stored in %s" % CREDENTIALS_PATH)

    return https_username, https_password


def get_credentials_path():
    """Return path to file containing credentials."""
    if os.path.isfile(CREDENTIALS_PATH):
        get_credentials()

    return CREDENTIALS_PATH
