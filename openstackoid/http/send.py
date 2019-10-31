# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative


from typing import Dict, Optional, Tuple

import functools

from requests import PreparedRequest

from .hooks import print_request_info
from ..dispatcher import scope
from ..interpreter import OidInterpreter
from ..utils import get_from_tuple, update_tuple


def send_extr_scp_func(interpreter: OidInterpreter,
                       *arguments, **keywords) -> Optional[Tuple]:
    request = get_from_tuple(PreparedRequest, arguments)
    service_type, service_scope = interpreter.get_service_scope(request)
    return service_type, service_scope


def send_args_xfm_func(interpreter: OidInterpreter, endpoint: str,
                       *arguments, **keywords) -> Tuple[Tuple, Dict]:
    request = get_from_tuple(PreparedRequest, arguments)
    interpreted = interpreter.iinterpret(request, endpoint=endpoint)
    interpreted.register_hook('response', print_request_info)
    args = update_tuple(request, interpreted, arguments)
    return args, keywords


send_scope = functools.partial(scope,
                               extr_scp_func=send_extr_scp_func,
                               args_xfm_func=send_args_xfm_func)
