# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative

import json
import logging

from requests import Session
from typing import Dict
from urllib import parse

import six

from ..oidinterpreter import get_oidinterpreter


logger = logging.getLogger(__name__)

SERVICES_CATALOG_PATH = "file:///vagrant/oidinterpreter/services.json"


# adapted using: 'from keystoneauth1.session import _sanitize_headers'
# defining this function here we also avoid import of keystoneauth1
def sanitize_headers(headers: Dict) -> Dict[str, str]:
    str_dict = {}
    for k, v in headers.items():
        if six.PY3:
            k = k.decode('ASCII') if isinstance(k, six.binary_type) else k
            if v is not None:
                v = v.decode('ASCII') if isinstance(v, six.binary_type) else v

                # decode url strings with special characters
                v = parse.unquote(v)

        else:
            k = k.encode('ASCII') if isinstance(k, six.text_type) else k
            if v is not None:
                v = v.encode('ASCII') if isinstance(v, six.text_type) else v
                v = parse.unquote(v)

        str_dict[k] = v

    return str_dict


# Monkey patch `Session.send` to add interpreter mechanism of openstackoid
session_send = Session.send


def _session_send_monkey_patch(cls, request, **kwargs):
    logger.warning("Patching session send with OidInterpreter")
    interpreter = get_oidinterpreter(SERVICES_CATALOG_PATH)
    _request = interpreter.iinterpret(request)
    logger.debug(f"FINAL request headers: {_request.headers}")
    return session_send(cls, _request, **kwargs)


# magic happens here!
Session.send = _session_send_monkey_patch
