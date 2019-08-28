import ast
import functools
import inspect
import json
import logging
import sys

from requests import Session, Request, Response
from openstackoid.interpreter import Service

import openstackoid.interpreter as oid


logger = logging.getLogger(__name__)
logging.basicConfig(format='\t%(levelname)s\t: %(message)s')
logger.setLevel(logging.DEBUG)


FILTERED = (ast.Load, ast.And, ast.Or, ast.BitOr, ast.BitAnd, ast.BitXor)

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

    def visit_Name(self, node):
        return EndpointDispatcher(node.id, request, interpreter)

    def visit_BinOp(self, node):
        # super call is required for implicit recursivity
        super(ScopeTransformer, self).generic_visit(node)
        operator = "__{}__".format(node.op.__class__.__name__[3:].lower())
        return getattr(node.left, operator)(node.right)


@functools.lru_cache(maxsize=5)
def cache_request(endpoint: str, request: Request, interpreter, **kwargs) -> Response:
    logger.warn(f"Caching request of endpoint: '{endpoint}'")
    session = Session()

    # must be immutable because request disappears after processed
    target_request = interpreter.iinterpret(request, atomic_scope=endpoint)
    prepared_request = target_request.prepare()
    response = session.send(prepared_request, **kwargs)
    logger.debug(f"\t[{response.status_code}] {response.url}")
    return response

class EndpointDispatcher:

    def __init__(self, endpoint: str, request: Request, interpreter):
        logger.debug(f"Identified endpoint: '{endpoint}'")
        self.endpoint = endpoint
        self.request = request
        self.interpreter = interpreter
        self._response = None

    @property
    def response(self) -> Response:
        if not self._response:
            self._response = cache_request(self.endpoint,
                                           self.request,
                                           self.interpreter)

        return self._response

    def __bool__(self):
        # Here lazy init is used with 'self.response' instead of 'self._response'
        return True if self.response and self.response.status_code == 200 else False

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


def dispatch(request, interpreter, verbose=False) -> Response:
    global_scope = interpreter.get_scope(request)
    target_service = interpreter.is_scoped_url(request)
    narrow_scope = global_scope[target_service.service_type]
    logger.info(f"Target scope: '{narrow_scope}'")
    tree = ast.parse(narrow_scope, mode ='eval')
    # logger.debug(f"Root Tree = {dump(tree)}")
    visit(tree.body)
    dispatcher = ScopeTransformer().visit(tree.body)
    # logger.debug(f"  ≡ {dispatcher}")
    return dispatcher.response


# A dummy identity service is required for proper interpretation of scope
identity = Service(service_type='identity',
                   cloud='Instance1',
                   url='https://www.phony.com/',
                   interface='admin')
invalid = Service(service_type='Search Engine',
               cloud='Instance0',
               # FIXME when dukduckgo instead of duckduckgo (without first 'c')
               url='https://www.dukduckgo.com/')
qwant = Service(service_type='Search Engine',
                cloud='Instance1',
                url='https://www.qwant.com/')
duckduckgo = Service(service_type='Search Engine',
              cloud='Instance2',
              url='https://www.duckduckgo.com/')

#narrow_scope = "Instance2 & ((Instance1 & Instance2) | (Instance2 & Instance1)) | Instance0"
narrow_scope = "Instance2 & (Instance0 | Instance1)"
#narrow_scope = "Instance0 | Instance1"
#narrow_scope = "Instance1"
scope = {'Search Engine': narrow_scope, 'identity': 'Instance1'}
headers = {'X-Scope': json.dumps(scope)}
request = Request('GET', f'{duckduckgo.url}?q=discovery', headers)

# Here the headers are set however the scope is not used. Therefore the request
# is sent to DuckDuckGo as a plain request.
# session = Session()
# print(session.send(request.prepare()).url)

# Now the interpreter uses the scope header to update the request Interprets the
# Scope says "use rather `Search Engine` in Instance1" and transforms DuckDuckGo
# into Qwant (using immutable interpretation), so a new request is created.
interpreter = oid.get_interpreter_from_services([identity, invalid, qwant, duckduckgo])
dispatch(request, interpreter, verbose=True)


print(cache_request.cache_info())
#print(session.send(irequest.prepare()).url)
