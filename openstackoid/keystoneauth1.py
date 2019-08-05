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

from .interpreter import get_interpreter


logger = logging.getLogger(__name__)

SERVICES_CATALOG_PATH = "file:///etc/openstackoid/catalog.json"


# Monkey patch `Session.send` to add interpreter mechanism of openstackoid
session_send = Session.send


def _session_send_monkey_patch(cls, request, **kwargs):
    logger.warning("Patching session send with OidInterpreter")
    interpreter = get_interpreter(SERVICES_CATALOG_PATH)
    _request = interpreter.iinterpret(request)
    logger.debug(f"FINAL request headers: {_request.headers}")
    return session_send(cls, _request, **kwargs)


# magic happens here!
Session.send = _session_send_monkey_patch
