# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

"""Module for http authentication operations."""

import getpass
import logging
import os

import keyring
import requests

from mozci.utils.transfer import path_to_file

AUTH = None
CREDENTIALS_PATH = path_to_file("credentials.cfg")
DIRNAME = os.path.dirname(CREDENTIALS_PATH)
KEYRING_KEY = 'ldap'
# We use buildapi since we don't have a better option
LDAP_HOST = 'https://secure.pub.build.mozilla.org/buildapi/self-serve'
LOG = logging.getLogger('mozci')


def _prompt_password_storing(https_username):
    https_password = getpass.getpass()
    store_password = raw_input(
        "Do you want to store your password in encrypted form (y or n)? ")

    if store_password == "y":
        keyring.set_password(KEYRING_KEY, https_username, https_password)

    return https_password


def _read_credentials():
    if not os.path.exists(DIRNAME):
        os.makedirs(DIRNAME)

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

    return content


def _first_run():
    https_username = raw_input("Please enter your full LDAP email address: ")
    LOG.info("We're going to ask you only *once* if you would like to store your password.")
    https_password = _prompt_password_storing(https_username)

    # Store user's email address
    with open(CREDENTIALS_PATH, "w+") as file_handler:
        file_handler.write("%s\n" % https_username)

    os.chmod(CREDENTIALS_PATH, 0600)
    LOG.info("The LDAP username has been stored in %s" % CREDENTIALS_PATH)

    return (https_username, https_password)


def get_credentials():
    """
    Return credentials for http access either from disk or directly
    from the user (which we store).
    """
    global AUTH
    # Use cached values
    if AUTH is not None:
        return AUTH

    # We can specify user and passwords through environment variables
    if 'LDAP_USER' in os.environ.keys() and 'LDAP_PW' in os.environ.keys():
        AUTH = (os.environ['LDAP_USER'], os.environ['LDAP_PW'])
        return AUTH

    content = None
    if os.path.isfile(CREDENTIALS_PATH):
        content = _read_credentials()

    if content is None:
        AUTH = _first_run()
    else:
        LOG.debug("Loading LDAP user from %s" % CREDENTIALS_PATH)
        https_username = content[0].strip()
        try:
            https_password = keyring.get_password(KEYRING_KEY, https_username)
        except:
            # The user has initially told us to not store the password in the
            # keyring OR the keyring is not working, hence, we ask again
            LOG.info("If you enter your password wrong we will prompt in the future if you want "
                     "to store your password.")
            https_password = getpass.getpass(
                "LDAP password for %s (PASSWORD WILL NOT BE STORED): " % https_username)

        AUTH = (https_username, https_password)

    return AUTH


def valid_credentials():
    """
    Verify that the user's credentials are valid.

    Raises an AuthenticationError if the credentials are invalid.
    """
    LOG.debug("Determine if the user's credentials are valid.")
    req = requests.get(LDAP_HOST, auth=get_credentials())
    if req.status_code == 401:
        remove_credentials()
        return False
    else:
        return True


def remove_credentials():
    """Removes the file stored at CREDENTIALS_PATH"""
    os.remove(CREDENTIALS_PATH)
    LOG.error("Your credentials were invalid. We have cleared the your auth "
              "information. Please start again.")


def get_credentials_path():
    """Return path to file containing credentials."""
    if os.path.isfile(CREDENTIALS_PATH):
        get_credentials()

    return CREDENTIALS_PATH
