# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative


from typing import Callable, Dict, Generic, Optional, Tuple, TypeVar

import ast
import functools
import logging

from .configuration import pop_execution_scope, push_execution_scope
from .interpreter import OidInterpreter
from .utils import print_func_signature


logger = logging.getLogger(__name__)


FILTERED_KEYS = (ast.Load, ast.And, ast.Or, ast.BitOr, ast.BitAnd, ast.BitXor)


T = TypeVar("T")


def _str(node: ast.AST) -> Optional[str]:
    name = None
    if not isinstance(node, FILTERED_KEYS):
        if isinstance(node, ast.BoolOp):
            operator = node.op.__class__.__name__.lower()
            values = ", ".join(_str(x) for x in node.values)
            name = f"{operator}({values})"
        elif isinstance(node, ast.BinOp):
            operator = node.op.__class__.__name__.lower()[3:]
            left = _str(node.left)
            right = _str(node.right)
            name = f"({left} {operator} {right})"
        elif isinstance(node, ast.Name):
            name = node.id
        else:
            raise TypeError

    return name


def _dump(node) -> str:
    return ast.dump(node,
                    annotate_fields=True,
                    include_attributes=False)


def _visit(node: ast.Expression, offset=0, verbose=False) -> None:
    if isinstance(node, ast.AST):
        name = _str(node)
        if name:
            if name.startswith("(") and name.endswith(')'):
                name = name[1:-1]
            level = "" if offset == 0 else f"{offset} "
            details = " - " + _dump(node) if verbose else ""
            logger.debug(f"{level}" + "_ " * offset + f"{name}{details}")

        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    _visit(item, offset=offset+1, verbose=verbose)
            else:
                _visit(value, offset=offset+1, verbose=verbose)


class OidDispatcher(Generic[T]):

    def __init__(
            self,
            interpreter: OidInterpreter,
            service_type: str,
            endpoint: str,
            func: Callable[..., T],
            bool_evl_func: Callable[..., bool],
            args_xfm_func: Callable[..., Tuple[Tuple, Dict]],
            disj_res_func: Callable[..., T],
            conj_res_func: Callable[..., T],
            *arguments, **keywords):
        self.interpreter = interpreter
        self.service_type = service_type
        self.endpoint = endpoint
        self.func = func
        self.bool_evl_func = bool_evl_func
        self.args_xfm_func = args_xfm_func
        self.disj_res_func = disj_res_func
        self.conj_res_func = conj_res_func
        self.arguments = arguments
        self.keywords = keywords
        self._result: Optional[T] = None

    @property
    def result(self) -> Optional[T]:
        if not self._result:
            self._result = self.run_func()

        return self._result

    @result.setter
    def result(self, value) -> None:
        self._result = value

    def __bool__(self):
        return self.bool_evl_func(self)

    def __or__(self, other):
        return self.disj_res_func(self, other)

    def __and__(self, other):
        return self.conj_res_func(self, other)

    def __str__(self):
        # return str(self.result)
        return f"{self.endpoint}" if self.endpoint else "None"

    def run_func(self) -> Optional[T]:
        args, kwargs = self.args_xfm_func(self.interpreter, self.endpoint,
                                          *self.arguments, **self.keywords)
        execution_scope = (self.service_type, self.endpoint)
        push_execution_scope(execution_scope)
        func = print_func_signature(self.func)
        result: T = func(*args, **kwargs)
        pop_execution_scope()
        logger.debug(result)
        return result


class ScopeTransformer(ast.NodeTransformer, Generic[T]):

    def __init__(self,
                 interpreter: OidInterpreter,
                 service_type: str,
                 func: Callable[..., T],
                 bool_evl_func: Callable[..., bool],
                 args_xfm_func: Callable[..., Tuple[Tuple, Dict]],
                 disj_res_func: Callable[..., OidDispatcher],
                 conj_res_func: Callable[..., OidDispatcher],
                 *arguments, **keywords):
        self.interpreter = interpreter
        self.service_type = service_type
        self.func: Callable[..., T] = func
        self.bool_evl_func: Callable[..., bool] = bool_evl_func
        self.args_xfm_func: Callable[..., Tuple[Tuple, Dict]] = args_xfm_func
        self.disj_res_func: Callable[..., OidDispatcher] = disj_res_func
        self.conj_res_func: Callable[..., OidDispatcher] = conj_res_func
        self.arguments = arguments
        self.keywords = keywords

    def visit_Name(self, node):
        logger.info(f"Processing '{node.id}'")
        return OidDispatcher(self.interpreter,
                             self.service_type,
                             node.id,
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
        if hasattr(node, "left") and hasattr(node, "right"):
            left = node.left
            right = node.right
        else:
            left = node.left if hasattr(node, 'left') else node.right
            right = OidDispatcher(None, None, lambda x: x, lambda x: False)

        logger.debug(f"Evaluating ({left} {operator[2:-2]} {right})")
        result = getattr(left, operator)(right)
        logger.info(f"Evaluation result: {result}")
        return result


default_bool_evl_func = lambda dispatcher: True if dispatcher.result else False  # noqa


default_args_xfm_func = lambda interpreter, endpoint, *args, **kwargs: (args, kwargs)  # noqa


default_disj_res_func = lambda this, other: this if this else other if other else None  # noqa


default_conj_res_func = lambda this, other: other if this and other else None  # noqa


def scope(interpreter: OidInterpreter,
          extr_scp_func: Callable[..., str],
          bool_evl_func: Callable[..., bool] = default_bool_evl_func,
          args_xfm_func: Callable[...,
                                  Tuple[Tuple, Dict]] = default_args_xfm_func,
          disj_res_func: Callable[..., OidDispatcher] = default_disj_res_func,
          conj_res_func: Callable[..., OidDispatcher] = default_conj_res_func):

    def decorator(func: Callable):

        @functools.wraps(func)
        def wrapper(*arguments, **keywords):
            logger.warning(f"Scoping '{func.__name__}' method")
            service_type, scope = extr_scp_func(interpreter,
                                                *arguments, **keywords)
            tree = ast.parse(scope, mode='eval')
            # logger.debug(f"\t= {_dump(tree)}")
            _visit(tree.body)
            dispatcher: OidDispatcher[T] = ScopeTransformer[T](
                interpreter,
                service_type,
                func,
                bool_evl_func,
                args_xfm_func,
                disj_res_func,
                conj_res_func,
                *arguments, **keywords).visit(tree.body)
            logger.info(f"\t= {dispatcher}")
            return dispatcher.result if dispatcher else None
        return wrapper
    return decorator
