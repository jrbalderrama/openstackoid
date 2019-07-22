# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative

import os

from typing import Dict
from urllib import parse

import six

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
