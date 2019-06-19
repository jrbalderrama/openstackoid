# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative

import os

from typing import Dict


DEFAULT_CLOUD_NAME = "CloudOne"


def _get_os_scope_service_env(service_name: str,
                              cloud_name: str) -> str:
    env_name = f"OS_SCOPE_{service_name.upper()}"
    value = os.environ.get(env_name)
    if value is None:
        value = os.environ.get("OS_REGION_NAME", cloud_name)

    return value


# adding optional argument to set it in the client
def get_default_scope(cloud_name: str=DEFAULT_CLOUD_NAME) -> Dict[str, str]:
    return {
        "compute": _get_os_scope_service_env("compute", cloud_name),
        "identity": _get_os_scope_service_env("identity", cloud_name),
        "image": _get_os_scope_service_env("image", cloud_name),
        "network": _get_os_scope_service_env("network", cloud_name),
        "placement": _get_os_scope_service_env("placement", cloud_name)
    }
