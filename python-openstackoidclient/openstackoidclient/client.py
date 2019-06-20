# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative
#
# See
# - https://docs.openstack.org/python-openstackclient/latest/contributor/plugins.html

"""
OpenStackClient plugin for OpenStackoïd.

Adds `--os-scope` global parameter:
--os-scope '{
  "compute": "OS_SCOPE_COMPUTE | OS_REGION_NAME",
  "identity": "OS_SCOPE_IDENTITY | OS_REGION_NAME",
  "image": "OS_SCOPE_IMAGE | OS_REGION_NAME",
  "network": "OS_SCOPE_NETWORK | OS_REGION_NAME",
  "placement": "OS_SCOPE_PLACEMENT | OS_REGION_NAME",
}' (Env: OS_SCOPE)
"""

import json
import logging

from requests import Session
from osc_lib import shell

from oidinterpreter.utils import scope


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

DEFAULT_API_VERSION = '1'

# API options required by the OSC plugin interface
API_NAME = 'openstackoid'

API_VERSION_OPTION = 'os_openstackoid_api_version'

API_VERSIONS = { '1': 'openstackoidclient.client' }


# Required by the OSC plugin interface
def build_option_parser(parser):
    """Hook to add global options

    Called from openstackclient.shell.OpenStackShell.__init__()
    after the builtin parser has been initialized.  This is
    where a plugin can add global options such as an API version setting.

    :param argparse.ArgumentParser parser: The parser object that has been
        initialized by OpenStackShell.
    """
    def _fmt_doc(service_name):
        return (
            f"{scope.DEFAULT_CLOUD_NAME} "
            f"(Env: OS_SCOPE_{service_name.upper()} | OS_REGION_NAME)")


    parser.add_argument(
        '--os-scope',
        metavar='<os_scope>',
        default=scope.get_default_scope(),
        help=("OpenStackoid Scope, "
              "default='%s'"
              % json.dumps({
                  "compute": _fmt_doc('compute'),
                  "identity": _fmt_doc('identity'),
                  "image": _fmt_doc('image'),
                  "network": _fmt_doc('network'),
                  "placement": _fmt_doc('placement')})))

    return parser


# -- 🐒 Monkey Patching 🐒
OS_SCOPE = None

# 1. Monkeypatch OpenStackShell.initialize_app to retrieve the scope value
#
# See,
# https://github.com/openstack/osc-lib/blob/aaf18dad8dd0b73db31aa95a6f2fce431c4cafda/osc_lib/shell.py#L390
initialize_app = shell.OpenStackShell.initialize_app


def _os_shell_monkey_patch(cls, argv):
    """Get the `os-scope` at the initialization of the app.

    Get the `os-scope` and put it into the `OS_SCOPE` global variable for
    latter use in `Session.request`.

    """
    global OS_SCOPE

    os_scope = scope.get_default_scope()
    shell_scope = cls.options.os_scope
    error_msg = ('--os-scope is not valid. see, '
                 '`openstack --help|fgrep -A 8 -- --os-scope`')

    if isinstance(shell_scope, dict):
        os_scope.update(shell_scope)
    elif isinstance(shell_scope, str):
        try:
            os_scope.update(json.loads(shell_scope))
        except ValueError:
            raise ValueError(error_msg)
    else:
        raise ValueError(error_msg)

    OS_SCOPE = os_scope
    logger.info("Save the current os-scope: ", OS_SCOPE)

    # XXX(rcherrueau): We remove the `os_scope` from the list of command
    # options (i.e., `cls.options`). We have to do so because of openstack
    # config loader [1] that strips the `os_` prefix of all options [2] and
    # deduces a specific configuration for the current cloud. Unfortunately,
    # `os_scope` becomes `scope` and hence gives a value to the `scope`
    # reserved keyword (I don't know which service exactly uses that keyword,
    # maybe policy from keystone [3]).
    #
    # [1]
    # https://github.com/openstack/openstacksdk/blob/stable/rocky/openstack/config/loader.py
    # [2]
    # https://github.com/openstack/openstacksdk/blob/5b15ccf042fafa14908ff1afe5a66cbce201d9ef/openstack/config/loader.py#L775-L781
    # [3]
    # https://docs.openstack.org/keystone/rocky/configuration/samples/policy-yaml.html
    del cls.options.os_scope

    return initialize_app(cls, argv)


shell.OpenStackShell.initialize_app = _os_shell_monkey_patch


# 2. Monkey patch `Session.request` to piggyback the scope with the keystone
# token.
#
# See,
# https://github.com/requests/requests/blob/64bde6582d9b49e9345d9b8df16aaa26dc372d13/requests/sessions.py#L466
session_request = Session.request


def _session_request_monkey_patch(cls, method, url, **kwargs):
    """Piggyback the `OS_SCOPE` on `X-Auth-Token`."""

    logger.warning("Patching session request")
    headers = kwargs.get("headers", {})

    # Put the scope in X-Scope header (there is always a scope)
    logger.info(f"Set the X-Scope header with {OS_SCOPE}...")
    scope_value = json.dumps(OS_SCOPE)
    headers["X-Scope"] = scope_value

    # Piggyback OS_SCOPE with X-Auth-Token
    if "X-Auth-Token" in headers:
        token = headers["X-Auth-Token"]
        logger.info(f"...to piggyback on token {token}")
        headers['X-Auth-Token'] = f"{token}!SCOPE!{scope_value}"
        logger.debug(f"Piggyback os-scope {repr(headers)}")

    return session_request(cls, method, url, **kwargs)


Session.request = _session_request_monkey_patch
