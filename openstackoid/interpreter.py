# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative

from dataclasses import dataclass
from typing import (Callable, Dict, List, Optional, NewType)

from requests import Request
from urllib import parse

import copy
import json
import logging
import os
import typing

from .utils import get_default_scope, sanitize_headers

# A service contains `Interface`, `Region`, `Service Type`, and `URL` keys.
Scope = NewType('Scope', Dict[str, str])

#logging.basicConfig(format='\t\t%(levelname)s - %(message)s', level=logging.DEBUG)
LOG = logging.getLogger(__name__)

SCOPE_DELIM = "!SCOPE!"

SCOPE_INTERPRETERS: Dict = {}


@dataclass
class Service:
    service_type: str
    cloud: str
    url: str
    interface: str = None


def oss2services(oss: List[Dict[str, str]]) -> List[Service]:
    """Transforms a list of OpenStack services into a list of Service.

    A list of OpenStack service may be obtain with

    openstack endpoint list --format json \
      -c "Service Type" -c "Interface" -c "URL" -c "Region"

    And then transformed into a python Dict with `json.load`.
    """
    return [Service(service_type=s["Service Type"],
                    cloud=s["Region"],
                    url=s["URL"],
                    interface=s["Interface"])
            for s in oss]


class OidInterpreter:
    """Interprets the `Scope` in a `Request` and update it."""

    def __init__(self, services: List[Service]):
        """Private: Use `get_interpreter instead`."""
        self.services = services
        LOG.debug(f'New OidInterpreter instance')

    def lookup_service(self, p: Callable[[Service], bool]) -> Service:
        """Finds the first Service that satisfies `p`.

        Looks-up into the list of services to find the first Service that
        satisfies the `p` predicate. `p` is a lambda that take a Service and
        returns a boolean. Raises `StopIterarion` if no service has been found.

        """
        try:
            service = next(s for s in self.services if p(s))
            LOG.info(f'Lookup found: {service} with predicate {p}')
            return service
        except StopIteration as s:
            LOG.info(f'No service found with predicate {p}')
            raise s

    def get_service(self, req: Request) -> Optional[Service]:
        """Tests if the `req` targets a Service.

        Returns the Service targeted by `req` if any.

        """
        service = None

        try:
            service = self.lookup_service(
                lambda s: req.url.startswith(s.url))
        finally:
            LOG.info(f'Scoped URL service: {service}')
            return service

    def get_scope(self, req: Request) -> Scope:
        """Finds the Scope from the current Request or set one by default.

        Seeks for the Scope in headers of `req`. Looks first into `X-Scope`,
        then into `X-Auth-Token` delimited by `SCOPE_DELIM`. Returns either the
        scope if found or a default scope containing the values of the local
        cloud otherwise.

        """
        final_scope = get_default_scope()
        headers = sanitize_headers(req.headers)
        if "X-Scope" in headers:
            scope_value = headers["X-Scope"]
            current_scope = json.loads(scope_value)
            final_scope = dict(final_scope, **current_scope)
            req.headers.update({ "X-Scope": json.dumps(final_scope) })
            LOG.debug("Scope set from X-Scope")
        if "X-Auth-Token" in headers:
            token = headers["X-Auth-Token"]
            if SCOPE_DELIM in token:
                token, scope_value = token.split(SCOPE_DELIM)
                current_scope = json.loads(scope_value)
                final_scope = dict(final_scope, **current_scope)
                LOG.debug("Scope set from X-Auth-Token")

            auth_scope = f"{token}{SCOPE_DELIM}{json.dumps(final_scope)}"
            req.headers.update({ "X-Auth-Token": auth_scope })

        LOG.info(f"Scope from headers: {final_scope}")
        return final_scope

    def clean_token_header(self, req: Request, token_header_name: str) -> None:
        """Cleans the token of `token_header_name` from the Scope in `req`.

        Updates `req` header in place.

        token_header_name is any valid header name that contains a keystone
        token (e.g., X-Auth-Token, X-Subject-Token).

        """
        headers = sanitize_headers(req.headers)
        if token_header_name in headers:
            auth_token = headers[token_header_name]
            if SCOPE_DELIM in auth_token:
                token, _ = auth_token.split(SCOPE_DELIM)
                req.headers.update({ token_header_name: token })
                LOG.info(f'Revert {token_header_name} to {token}')


    def get_service_scope(self, req: Request) -> Optional[str]:
        """Get the scope of a targeted service type.

        """
        result = None
        scope = self.get_scope(req)
        service = self.get_service(req)
        if service:
            result = scope[service.service_type]

        return result

    def interpret(self, req: Request, endpoint: str=None) -> None:
        """Finds & interprets the scope to update `req` if need be.

        Update `req` in place with the new headers and url. If `endpoint` is set
        do not resolve cloud name and use the provided endpoint instead.

        """
        # Get the scope and the service originally targeted
        scope = self.get_scope(req)
        service = self.get_service(req)

        # The current request doesn't target a scoped service,
        # so we don't change the request
        if not service:
            LOG.debug("Any scoped service found for the request")
            return

        # Find the targeted cloud
        targeted_service_type = service.service_type
        targeted_interface = service.interface

        # In simple situations (when the scope does not contain an expression,
        # e.g., scope with operator) the cloud endpoint is the name of the
        # identifier set in the scope of the original scoped service
        targeted_cloud = endpoint if endpoint else scope[targeted_service_type]
        LOG.info(f"Effective endpoint: {targeted_cloud}")

        # From targeted cloud, find the targeted service
        targeted_service = self.lookup_service(
            lambda s:
                s.interface == targeted_interface and
                s.service_type == targeted_service_type and
                s.cloud == targeted_cloud)

        # Update request
        # 1. Change url
        req.url = req.url.replace(service.url, targeted_service.url)
        # 2. Remove scope from token
        self.clean_token_header(req, 'X-Subject-Token')
        if targeted_service_type == 'identity':
            self.clean_token_header(req, 'X-Auth-Token')

        # 3. Update contents
        req.headers.update({'X-Scope': json.dumps(scope)})

        # HACK: Find the identity service. This part is used later to add
        # helpful headers to tweak the keystone middleware.
        #
        # The system env var OS_REGION_NAME must be defined to get the
        # proper default scope, otherwise 'CloudOne' is set from oid.utils
        if targeted_service_type == 'identity':
            try:
                id_service = self.lookup_service(
                    lambda s:
                        s.interface == 'admin' and
                        s.service_type == 'identity' and
                        s.cloud == scope['identity'])

                req.headers.update({
                    'X-Identity-Cloud': id_service.cloud,
                    'X-Identity-Url': id_service.url,
                })
            except StopIteration:
                LOG.error(f"Invalid identity scope: {scope['identity']}")
                raise ValueError

    def iinterpret(self, req: Request, endpoint:str = None) -> Request:
        "Immutable version of `interpret`."
        req2 = copy.deepcopy(req)
        self.interpret(req2, endpoint=endpoint)
        return req2


def get_interpreter(services_uri: str) -> OidInterpreter:
    """Factory method that instantiates a new OidInterpreter.

    services_uri is the url of the services list. In absence of scheme, the
    Default is `file://` uri that should target a json file.

    Right now, we only support filepath uri.

    """
    services: List[Service] = []
    uri = parse.urlparse(services_uri)

    if uri not in SCOPE_INTERPRETERS:
        # Interpret the uri to get the service list. E.g.,
        # if uri.scheme == 'sql', uri.scheme == 'file' ...
        # Right now, we only support filepath uri
        fp = os.path.abspath(''.join([uri.netloc, uri.path]))
        with open(fp, 'r') as services_json:
            services = oss2services(json.load(services_json))
            LOG.debug(f'Loaded from {services_uri} the services {services}')

    # Instantiate & serialize the OidInterpreter
    return SCOPE_INTERPRETERS.setdefault(uri, OidInterpreter(services))


def get_interpreter_from_services(
       services: List[Service]) -> OidInterpreter:
    """OidInterpreter factory from a list of services.

    """
    return OidInterpreter(services)
