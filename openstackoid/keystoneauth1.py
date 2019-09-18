# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative

from requests import Session

import logging

from .interpreter import get_interpreter
from .dispatcher import requests_scope


logger = logging.getLogger(__name__)

SERVICES_CATALOG_PATH = "file:///etc/openstackoid/catalog.json"

interpreter = get_interpreter(SERVICES_CATALOG_PATH)
logger.warning("Monkey patching `Session.send` with OidDispatcher")
Session.send = requests_scope(interpreter)(Session.send)
