# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative

import ast
import logging

from requests import Session, Request, Response
from typing import Callable, Optional


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


class ScopeTransformer(ast.NodeTransformer):

    def __init__(self, interpreter, session_send: Callable[..., Response],
                 session: Session, request: Request, **keywords):
        self.interpreter = interpreter
        self.session_send = session_send
        self.session = session
        self.request = request
        self.keywords = keywords

    def visit_Name(self, node):
        return OidDispatcher(node.id, self.interpreter, self.session_send,
                             self.session, self.request, **self.keywords)

    def visit_BinOp(self, node):
        # super call is required for implicit recursivity
        super(ScopeTransformer, self).generic_visit(node)
        operator = "__{}__".format(node.op.__class__.__name__[3:].lower())
        return getattr(node.left, operator)(node.right)


def session_request(endpoint: str, interpreter, session_send: Callable[..., Response],
                    session: Session, request: Request, **keywords) -> Response:
    # must be immutable because request disappears after processed
    target_request = interpreter.iinterpret(request, atomic_scope=endpoint)
    response = session_send(session, target_request, **keywords)
    logger.debug(f"\t[{response.status_code}] {response.url}")
    return response


class OidDispatcher:

    def __init__(self, endpoint: str, interpreter, session_send: Callable[..., Response],
                 # response_merger: Callable[..., Response]=lambda x:x,
                 session: Session, request: Request, **keywords):
        logger.warning(f"\tFinal endpoint for session request: '{endpoint}'")
        self.endpoint = endpoint
        self.interpreter = interpreter
        self.session_send = session_send
        self.session = session
        self.request = request
        self.keywords = keywords
        self._response: Optional[Response] = None

    @property
    def response(self) -> Response:
        if not self._response:
            self._response = session_request(self.endpoint,
                                             self.interpreter,
                                             self.session_send,
                                             self.session,
                                             self.request,
                                             **self.keywords)

        return self._response

    def __bool__(self) -> bool:
        # Here a lazy init with 'self.response' instead of 'self._response'
        return True \
            if self.response and self.response.status_code in [200, 201] \
               else False

    def __or__(self, other):
        if self:
            return self
        if other:
            return other

    def __and__(self, other):
        if self and other:
            # TODO Merge responses before return final response
            # return response_merger(self.response, other.response)
            return other

    def __str__(self):
        return self.endpoint


def dispatch(interpreter, session_send: Callable[..., Response],
             session: Session, request: Request, **keywords) -> Response:
    global_scope = interpreter.get_scope(request)
    target_service = interpreter.is_scoped_url(request)
    narrow_scope = global_scope[target_service.service_type]
    logger.info(f"\tScope: '{narrow_scope}'")
    tree = ast.parse(narrow_scope, mode ='eval')
    # logger.debug(f"\t= {dump(tree)}")
    visit(tree.body)
    dispatcher = ScopeTransformer(
        interpreter, session_send,
        session, request, **keywords).visit(tree.body)
    logger.info(f"\t= {dispatcher}")
    return dispatcher.response
