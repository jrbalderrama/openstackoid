# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative


from typing import Any, Optional, Tuple

import copy
import threading


DEFAULT_CLOUD_NAME = "CloudOne"


# FIXME spell better and remove scheme
SERVICES_CATALOG_PATH = "file:///etc/openstackoid/catalog.json"


__local_context = threading.local()


def _get_from_context(name: str) -> Optional[Any]:
    return getattr(__local_context, name, None)


def _push_to_context(name: str, value: Any) -> None:
    setattr(__local_context, name, value)


def get_shell_scope() -> Optional[dict]:
    # get a copy and preserve original value
    return copy.copy(_get_from_context("shell_scope"))


def push_shell_scope(value: dict) -> None:

    # set shell scope only once during execution
    scope = get_shell_scope()
    if not scope:
        if not isinstance(value, dict):
            raise TypeError("Shell scope must be a dictionary.")

        _push_to_context("shell_scope", value)


def get_execution_scope() -> Optional[Tuple]:
    return _get_from_context("atomic_scope")


def push_execution_scope(value: Tuple) -> None:
    if not isinstance(value, tuple):
        raise TypeError("Atomic scope must be a tuple.")

    if any(operator in value[1] for operator in "|&"):
        raise ValueError("Atomic scope must not include operators.")

    _push_to_context("atomic_scope", value)
