# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative

import ast
# import functools
import logging

from requests import Session, Request, Response


FILTERED = (ast.Load, ast.And, ast.Or, ast.BitOr, ast.BitAnd, ast.BitXor)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def to_str(node):
    name = None
    if not isinstance(node, FILTERED):
        if isinstance(node, ast.BoolOp):
            operator = node.op.__class__.__name__.lower()
            values = ", ".join(to_str(x) for x in node.values)
            name = f"{operator}({values})"
        elif isinstance(node, ast.BinOp):
            operator = node.op.__class__.__name__.lower()
            left = to_str(node.left)
            right = to_str(node.right)
            name = f"{left} {operator} {right}"
        elif isinstance(node, ast.Name):
            name = node.id.lower()
        else:
            raise TypeError

        return name


def dump(node):
    return ast.dump(node,
                    annotate_fields=True,
                    include_attributes=False)


def visit(node, offset=0, dump=False):
    if isinstance(node, ast.AST):
        name = to_str(node)
        if name:
            if dump:
                logger.info("_ " * offset + name + " - " + dump(node))
            else:
                logger.info("_ " * offset + name)
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    visit(item, offset=offset+1)
            else:
                visit(value, offset=offset+1)


class ScopeTransformer(ast.NodeTransformer):

    def __init__(self, request: Request, interpreter):
        self.request = request
        self.interpreter = interpreter

    def visit_Name(self, node):
        return OidDispatcher(node.id, self.request, self.interpreter)

    def visit_BinOp(self, node):
        # super call is required for implicit recursivity
        super(ScopeTransformer, self).generic_visit(node)
        operator = "__{}__".format(node.op.__class__.__name__[3:].lower())
        return getattr(node.left, operator)(node.right)


#@functools.lru_cache(maxsize=5)
def cache_request(endpoint: str, request: Request, interpreter, **kwargs) -> Response:
    logger.warn(f"Caching request of endpoint: '{endpoint}'")
    session = Session()

    # must be immutable because request disappears after processed
    target_request = interpreter.iinterpret(request, atomic_scope=endpoint)
    prepared_request = target_request.prepare()
    response = session.send(prepared_request, **kwargs)
    logger.debug(f"\t[{response.status_code}] {response.url}")
    return response


class OidDispatcher:

    def __init__(self, endpoint: str, request: Request, interpreter, **kwargs):
        logger.debug(f"Identified endpoint: '{endpoint}'")
        self.endpoint = endpoint
        self.request = request
        self.interpreter = interpreter
        self._response = None
        self.keywords = kwargs

    @property
    def response(self) -> Response:
        if not self._response:
            self._response = cache_request(self.endpoint,
                                           self.request,
                                           self.interpreter,
                                           **self.keywords)

        return self._response

    def __bool__(self):
        # Here a lazy init with 'self.response' instead of 'self._response'
        return True \
            if self.response and self.response.status_code == 200 \
               else False

    def __or__(self, other):
        if self:
            return self
        if other:
            return other

    def __and__(self, other):
        if self and other:
            return other

    def __str__(self):
        return self.endpoint


def dispatch(request: Request, interpreter) -> Response:
    global_scope = interpreter.get_scope(request)
    target_service = interpreter.is_scoped_url(request)
    narrow_scope = global_scope[target_service.service_type]
    logger.info(f"Target scope: '{narrow_scope}'")
    tree = ast.parse(narrow_scope, mode ='eval')
    # logger.debug(f"Root Tree = {dump(tree)}")
    visit(tree.body)
    dispatcher = ScopeTransformer(request, interpreter).visit(tree.body)
    # logger.debug(f"  ≡ {dispatcher}")
    return dispatcher.response
