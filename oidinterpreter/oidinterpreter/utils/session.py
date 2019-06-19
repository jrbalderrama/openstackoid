# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative

import json
import logging
import requests

from typing import Dict
from urllib import parse

import six

from ..oidinterpreter import get_oidinterpreter


SERVICES_CATALOG_PATH = "file:///vagrant/oidinterpreter/services.json"

LOG = logging.getLogger(__name__)

requests.sessions.Session.old_send = requests.sessions.Session.send


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


def _override_send(self, request, **kwargs):
    interpreter = get_oidinterpreter(SERVICES_CATALOG_PATH)
    final_request = interpreter.iinterpret(request)
    LOG.debug(f"FINAL request headers: {final_request.headers}")
    return self.old_send(final_request, **kwargs)


def _request_monkey_patch() -> None:
    LOG.warning("Patching request with oidinterpreter")
    requests.sessions.Session.send = _override_send


# magic happens here!
_request_monkey_patch()
