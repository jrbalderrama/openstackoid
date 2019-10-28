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

from ..dispatcher import OidDispatcher, scope
from ..interpreter import OidInterpreter


logger = logging.getLogger(__name__)


def image_list_extr_scp_func(interpreter: OidInterpreter,
                             *arguments, **keywords) -> Optional[Tuple]:
    context = arguments[0]
    shell_scope = context.app.options.oid_scope
    service_scope = shell_scope["image"]
    logger.info(f"Service scope: '{service_scope}'")
    return "image", service_scope


def image_list_conj_res_func(
        this: OidDispatcher, other: OidDispatcher) -> OidDispatcher:
    if this.result and other.result:
        # add cloud name to each result before aggregation
        aggregated_labels = ("Cloud",) + other.result[0]
        this_generator = ((this.endpoint,) + i for i in this.result[1])
        other_generator = ((other.endpoint,) + o for o in other.result[1])
        aggregated_results = itertools.chain(this_generator, other_generator)
        other.result = (aggregated_labels, aggregated_results)

    return other


image_list_scope = functools.partial(scope,
                                     extr_scp_func=image_list_extr_scp_func,
                                     conj_res_func=image_list_conj_res_func)
