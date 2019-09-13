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
                 bool_evl_func: Callable[..., bool],
                 args_xfm_func: Callable[..., Tuple[Tuple, Dict]],
                 disj_res_func: Callable[..., T],
                 conj_res_func: Callable[..., T],
                 *arguments, **keywords):
        self.func: Callable[..., T] = func
        self.bool_evl_func: Callable[..., bool] = bool_evl_func
        self.args_xfm_func: Callable[..., Tuple[Tuple, Dict]] = args_xfm_func
        self.disj_res_func: Callable[..., T] = disj_res_func
        self.conj_res_func: Callable[..., T] = conj_res_func
        self.arguments = arguments
        self.keywords = keywords

    def visit_Name(self, node):
        logger.info(f"Processing '{node.id}'")
        return OidDispatcher(node.id,
                             self.func,
                             self.bool_evl_func,
                             self.args_xfm_func,
                             self.disj_res_func,
                             self.conj_res_func,
                             *self.arguments, **self.keywords)

    def visit_BinOp(self, node):
        # Call 'super' method is required for implicit recursivity
        super(ScopeTransformer, self).generic_visit(node)
        operator = "__{}__".format(node.op.__class__.__name__[3:].lower())
        result = None
        if hasattr(node, 'left') and hasattr(node, 'right'):
            logger.info(f"Evaluating ({node.left} {operator[2:-2]} {node.right})")
            result = getattr(node.left, operator)(node.right)
        elif hasattr(node, 'left'):
            # there is no 'right' attribute
            # return 'left' to enable operator pipelining : <?> | (None | None)
            result = node.left
        elif hasattr(node, 'right'):
            # there is no 'left' attribute
            # return 'right' to enable operator pipelining : None | None | <?>
            result = node.right
        else:
            # this case should never happen
            logger.warning("Operator evaluation with 'None' value")
        return result


default_disj_func=lambda *x: x[0] if x[0] else x[1] if x[1] else None
default_conj_func=lambda *x: x[1] if x[0] and x[1] else None


class OidDispatcher(Generic[T]):

    def __init__(self, endpoint: str,
                 func: Callable[..., T],
                 bool_evl_func: Callable[..., bool],
                 args_xfm_func: Callable[..., Tuple[Tuple, Dict]],
                 disj_res_func: Callable[..., T],
                 conj_res_func: Callable[..., T],
                 *arguments, **keywords):
        self.endpoint = endpoint
        self.func: Callable[..., T] = func
        self.bool_evl_func: Callable[..., bool] = bool_evl_func
        self.args_xfm_func: Callable[..., Tuple[Tuple, Dict]] = args_xfm_func
        self.disj_res_func: Callable[..., T] = disj_res_func
        self.conj_res_func: Callable[..., T] = conj_res_func
        self.arguments = (endpoint,) + arguments
        self.keywords = keywords
        self._result: Optional[T] = None

    @property
    def result(self) -> Optional[T]:
        if not self._result:
            self._result = OidDispatcher[T].func_wrapper(
                self.func, self.args_xfm_func,
                *self.arguments, **self.keywords)

        return self._result

    @result.setter
    def result(self, value) -> None:
        self._result = value

    def __bool__(self) -> bool:
        return self.bool_evl_func(self)

    def __or__(self, other) -> T:
        return self.disj_res_func(self, other)

    def __and__(self, other) -> T:
        return self.conj_res_func(self, other)

    def __str__(self) -> str:
        return self.endpoint

    @staticmethod
    def func_wrapper(func: Callable[..., T],
                     args_xfm_func: Callable[..., Tuple[Tuple, Dict]],
                     *arguments, **keywords) -> Optional[T]:
        args, kwargs = args_xfm_func(*arguments, **keywords)
        result: T = func(*args, **kwargs)
        logger.debug(result)
        return result

    @staticmethod
    def scope(interpreter: OidInterpreter,
              extr_scp_func: Callable[..., str]=None,
              bool_evl_func: Callable[..., bool]=None,
              args_xfm_func: Callable[..., Tuple[Tuple, Dict]]=None,
              disj_res_func: Callable[..., T]=None,
              conj_res_func: Callable[..., T]=None):
        def decorator(func:Callable):
            @functools.wraps(func)
            def wrapper(*arguments, **keywords):
                scope = extr_scp_func(*arguments + (interpreter,), **keywords)
                tree = ast.parse(scope, mode ='eval')
                # logger.debug(f"\t= {dump(tree)}")
                visit(tree.body)
                dispatcher: OidDispatcher[T] = ScopeTransformer[T](
                    func,
                    bool_evl_func,
                    args_xfm_func,
                    disj_res_func,
                    conj_res_func,
                    *arguments + (interpreter,), **keywords).visit(tree.body)
                logger.info(f"\t= {dispatcher}")
                return dispatcher.result if dispatcher else None
            return wrapper
        return decorator


def _get_interpreter(*arguments) -> OidInterpreter:
    return next(a for a in arguments if isinstance(a, OidInterpreter))


def _get_request(*arguments) -> PreparedRequest:
    return next(a for a in arguments if isinstance(a, PreparedRequest))


def requests_extr_scp_func(*arguments, **keywords) -> str:
    interpreter = _get_interpreter(*arguments)
    request = typing.cast(Request, _get_request(*arguments))
    global_scope = interpreter.get_scope(request)
    target_service = interpreter.is_scoped_url(request)
    narrow_scope = global_scope[target_service.service_type]
    logger.info(f"\tScope: '{narrow_scope}'")
    return narrow_scope


def requests_args_xfm_func(*arguments, **keywords) -> Tuple[Tuple, Dict]:
    interpreter = _get_interpreter(*arguments)
    endpoint = next(a for a in arguments if isinstance(a, str))
    session = next(a for a in arguments if isinstance(a, Session))
    _request = typing.cast(Request, _get_request(*arguments))

    # must be immutable because request disappears after processed
    request: Request = interpreter.iinterpret(_request, atomic_scope=endpoint)

    return (session, request), keywords


def requests_bool_evl_func(instance) -> bool:
    return True \
        if instance.result and \
           typing.cast(Response, instance._result).status_code in [200, 201] \
           else False


requests_scope = functools.partial(OidDispatcher[Response].scope,
                                   extr_scp_func=requests_extr_scp_func,
                                   bool_evl_func=requests_bool_evl_func,
                                   args_xfm_func=requests_args_xfm_func,
                                   disj_res_func=default_disj_func,
                                   conj_res_func=default_conj_func)
