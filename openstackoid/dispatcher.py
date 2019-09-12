# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative

from requests import Session, Request, PreparedRequest, Response
from typing import Any, Callable, Dict, Generic, Optional, Tuple, TypeVar

import ast
import functools
import logging
import typing

from .interpreter import OidInterpreter, Service


SERVICES_CATALOG_PATH = "file:///etc/openstackoid/catalog.json"

FILTERED = (ast.Load, ast.And, ast.Or, ast.BitOr, ast.BitAnd, ast.BitXor)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def to_str(node: ast.AST) -> Optional[str]:
    name = None
    if not isinstance(node, FILTERED):
        if isinstance(node, ast.BoolOp):
            operator = node.op.__class__.__name__.lower()
            values = ", ".join(to_str(x) for x in node.values)
            name = f"{operator}({values})"
        elif isinstance(node, ast.BinOp):
            operator = node.op.__class__.__name__.lower()[3:]
            left = to_str(node.left)
            right = to_str(node.right)
            name = f"({left} {operator} {right})"
        elif isinstance(node, ast.Name):
            name = node.id
        else:
            raise TypeError

    return name


def dump(node) -> str:
    return ast.dump(node,
                    annotate_fields=True,
                    include_attributes=False)


def visit(node: ast.Expression, offset=0, verbose=False) -> None:
    if isinstance(node, ast.AST):
        name = to_str(node)
        if name:
            if name.startswith("(") and name.endswith(')'):
                name = name[1:-1]
            level = "" if offset == 0 else f"{offset} "
            details = " - " + dump(node) if verbose else ""
            logger.debug(f"{level}" + "_ " * offset + f"{name}{details}")

        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    visit(item, offset=offset+1)
            else:
                visit(value, offset=offset+1)


T = TypeVar("T")


class ScopeTransformer(ast.NodeTransformer, Generic[T]):

    def __init__(self,
                 func: Callable[..., T],
                 bool_eval_func: Callable[..., bool],
                 disj_res_func: Callable[..., T],
                 conj_res_func: Callable[..., T],
                 args_xform_func: Callable[..., Tuple[Tuple, Dict]],
                 *arguments, **keywords):
        self.func: Callable[..., T] = func
        self.bool_eval_func: Callable[..., bool] = bool_eval_func
        self.disj_res_func: Callable[..., T] = disj_res_func
        self.conj_res_func: Callable[..., T] = conj_res_func
        self.args_xform_func = args_xform_func
        self.arguments = arguments
        self.keywords = keywords

    def visit_Name(self, node):
        logger.info(f"Processing '{node.id}'")
        return OidDispatcher(node.id,
                             self.func,
                             self.bool_eval_func,
                             self.disj_res_func,
                             self.conj_res_func,
                             self.args_xform_func,
                             *self.arguments, **self.keywords)

    def visit_BinOp(self, node):
        # super call is required for implicit recursivity
        super(ScopeTransformer, self).generic_visit(node)
        operator = "__{}__".format(node.op.__class__.__name__[3:].lower())
        logger.info(f"Evaluating ({node.left} {operator[2:-2]} {node.right})")
        return getattr(node.left, operator)(node.right)


def get_interpreter(*arguments) -> OidInterpreter:
    return next(a for a in arguments if isinstance(a, OidInterpreter))


def get_request(*arguments) -> PreparedRequest:
    return next(a for a in arguments if isinstance(a, PreparedRequest))


def get_narrow_scope(*arguments) -> str:
    interpreter = get_interpreter(*arguments)
    request = typing.cast(Request, get_request(*arguments))
    global_scope = interpreter.get_scope(request)
    target_service = interpreter.is_scoped_url(request)
    narrow_scope = global_scope[target_service.service_type]
    logger.info(f"\tScope: '{narrow_scope}'")
    return narrow_scope


default_conj_func=lambda *x: x[1] if x[0] and x[1] else None
default_disj_func=lambda *x: x[0] if x[0] else x[1] if x[1] else None


def requests_args_xform_func(*arguments, **keywords) -> Tuple[Tuple, Dict]:
    interpreter = get_interpreter(*arguments)
    endpoint = next(a for a in arguments if isinstance(a, str))
    session = next(a for a in arguments if isinstance(a, Session))
    _request = typing.cast(Request, get_request(*arguments))

    # must be immutable because request disappears after processed
    request: Request = interpreter.iinterpret(_request, atomic_scope=endpoint)

    return (session, request), keywords


def requests_bool_eval_func(instance) -> bool:
    # Here a lazy init with 'self.response' instead of 'self._response'
    return True \
        if instance.result and \
           typing.cast(Response, instance.result).status_code in [200, 201] \
           else False


class OidDispatcher(Generic[T]):

    def __init__(self, endpoint: str,
                 func: Callable[..., T],
                 bool_eval_func: Callable[..., bool],
                 disj_res_func: Callable[..., T],
                 conj_res_func: Callable[..., T],
                 args_xform_func: Callable[..., Tuple[Tuple, Dict]],
                 *arguments, **keywords):
        self.endpoint = endpoint
        self.func: Callable[..., T] = func
        self.bool_eval_func: Callable[..., bool] = bool_eval_func
        self.disj_res_func: Callable[..., T] = disj_res_func
        self.conj_res_func: Callable[..., T] = conj_res_func
        self.args_xform_func = args_xform_func
        self.arguments = (self.endpoint,) + arguments
        self.keywords = keywords
        self._result: Optional[T] = None

    @property
    def result(self) -> T:
        if not self._result:
            self._result = OidDispatcher.func_wrapper(
                self.func, self.args_xform_func,
                *self.arguments, **self.keywords)

        return self._result

    def __bool__(self) -> bool:
        return self.bool_eval_func(self)

    def __or__(self, other) -> T:
        return self.disj_res_func(self, other)

    def __and__(self, other) -> T:
        return self.conj_res_func(self, other)

    def __str__(self) -> str:
        return self.endpoint

    @staticmethod
    def func_wrapper(func: Callable[..., T],
                     args_xform_func: Callable[..., Tuple[Tuple, Dict]],
                     *arguments, **keywords) -> T:
        args, kwargs = args_xform_func(*arguments, **keywords)
        result: T = func(*args, **kwargs)
        logger.info(result)
        return result

    @staticmethod
    def scope(func: Callable, bool_eval_func: Callable[..., bool],
               args_xform_func: Callable[..., Tuple[Tuple, Dict]],
               disj_res_func: Callable[..., T], conj_res_func: Callable[..., T]):
        @functools.wraps(func)
        def wrapper(*arguments, **keywords):
            expression = get_narrow_scope(*arguments)
            tree = ast.parse(expression, mode ='eval')
            # logger.debug(f"\t= {dump(tree)}")
            visit(tree.body)
            dispatcher: OidDispatcher[T] = ScopeTransformer[T](
                func, bool_eval_func, disj_res_func,
                conj_res_func, args_xform_func,
                *arguments, **keywords).visit(tree.body)
            logger.info(f"\t= {dispatcher}")
            return dispatcher.result
        return wrapper

    requests_scope = functools.partialmethod(scope,
                                             Session.send,
                                             requests_bool_eval_func,
                                             requests_args_xform_func,
                                             default_disj_func,
                                             default_conj_func)
