# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative


from typing import Optional, Tuple

import functools
import itertools
import logging

from ..configuration import get_shell_scope
from ..dispatcher import OidDispatcher, scope
from ..interpreter import OidInterpreter


logger = logging.getLogger(__name__)


def default_osc_extr_scp_func(interpreter: OidInterpreter,
                              *arguments, **keywords) -> Optional[Tuple]:
    # openstackclient.image.v2.image.ListImage
    # openstackclient.compute.v2.server.CreateServer
    client_entry_point = arguments[0]
    service_type = client_entry_point.__class__.__module__.split('.')[1]
    shell_scope = get_shell_scope()
    service_scope = shell_scope.get(service_type)
    logger.info(f"Service scope: '{service_scope}'")
    return service_type, service_scope


def default_command_lister_conf_res_func(
        this: OidDispatcher, other: OidDispatcher) -> OidDispatcher:
    if this.result and other.result:
        other.result = (other.result[0],
                        itertools.chain(this.result[1], other.result[1]))

    return other


def default_command_showone_conj_res_func(
        this: OidDispatcher, other: OidDispatcher) -> OidDispatcher:
    if this.result and other.result:
        other.result = (i + o for i, o in zip(this.result, other.result))

    return other


default_osc_lister_scope = functools.partial(
    scope,
    extr_scp_func=default_osc_extr_scp_func,
    conj_res_func=default_command_lister_conf_res_func)


default_osc_showone_scope = functools.partial(
    scope,
    extr_scp_func=default_osc_extr_scp_func,
    conj_res_func=default_command_showone_conj_res_func)
