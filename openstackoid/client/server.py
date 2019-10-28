# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative


from typing import Optional, Tuple

import functools
import logging

from ..dispatcher import OidDispatcher, scope
from ..interpreter import OidInterpreter


logger = logging.getLogger(__name__)


def compute_create_extr_scp_func(interpreter: OidInterpreter,
                                 *arguments, **keywords) -> Optional[Tuple]:
    # context openstackclient.compute.v2.server.CreateServer
    context = arguments[0]
    shell_scope = context.app.options.oid_scope
    service_scope = shell_scope["compute"]
    logger.info(f"Service scope: '{service_scope}'")
    return "compute", service_scope


def compute_create_conj_res_func(
        this: OidDispatcher, other: OidDispatcher) -> OidDispatcher:
    if this.result and other.result:
        aggregated = (i + o for i, o in zip(this.result, other.result))
        other.result = aggregated

    return other


compute_create_scope = functools.partial(
    scope,
    extr_scp_func=compute_create_extr_scp_func,
    conj_res_func=compute_create_conj_res_func)
