# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative


from typing import Any, Optional

import copy
import threading


DEFAULT_CLOUD_NAME = "CloudOne"


EXECUTION_SCOPE = "atomic_scope"


# FIXME spell better and remove scheme
SERVICES_CATALOG_PATH = "file:///etc/openstackoid/catalog.json"


__local_context = threading.local()


def _get_from_context(name: str) -> Optional[Any]:
    return getattr(__local_context, name, None)


def _push_to_context(name: str, value: Any) -> None:
    setattr(__local_context, name, value)


def get_shell_scope() -> Optional[dict]:
    # Make shell scope immutable
    shell_scope = _get_from_context("shell_scope")
    return copy.copy(shell_scope)


def push_shell_scope(value: dict) -> None:

    # set shell scope only once during execution
    scope = get_shell_scope()
    if not scope:
        if not isinstance(value, dict):
            raise TypeError("Shell scope must be a dictionary.")

        _push_to_context("shell_scope", value)


def get_execution_scope() -> Optional[tuple]:
    stack = _get_from_context(EXECUTION_SCOPE)
    return stack[-1] if stack else None


def push_execution_scope(value: tuple) -> None:
    if not isinstance(value, tuple):
        raise TypeError("Atomic scope must be a tuple.")

    if any(operator in value[1] for operator in "|&^"):
        raise ValueError("Atomic scope must not include operators.")

    stack = _get_from_context(EXECUTION_SCOPE)
    if stack:
        stack.append(value)
    else:
        stack = [value]

    _push_to_context(EXECUTION_SCOPE, stack)


def pop_execution_scope() -> Optional[tuple]:
    stack = _get_from_context(EXECUTION_SCOPE)
    return stack.pop() if stack else None
