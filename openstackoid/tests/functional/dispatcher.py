# -*- coding: utf-8 -
#   ____                ______           __        _    __
#  / __ \___  ___ ___  / __/ /____ _____/ /_____  (_)__/ /
# / /_/ / _ \/ -_) _ \_\ \/ __/ _ `/ __/  '_/ _ \/ / _  /
# \____/ .__/\__/_//_/___/\__/\_,_/\__/_/\_\\___/_/\_,_/
#     /_/
# Make your OpenStacks Collaborative

from requests import Request, Response, Session

import json
import logging
import urllib3

from openstackoid.interpreter import Service
from openstackoid.dispatcher import requests_scope, OidDispatcher

import openstackoid.interpreter as oid


logger = logging.getLogger(__name__)


logging.basicConfig(format='\t%(levelname)s\t: %(message)s')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# A dummy identity service is required for proper interpretation of scope
identity = Service(service_type='identity',
                   cloud='Instance0',
                   url='https://www.phony.com/',
                   interface='admin')
# dukduckgo instead of duckduckgo (without first 'c') for a 403 response
invalid = Service(service_type='Search Engine',
               cloud='Instance1',
               url='https://www.dukduckgo.com/')
qwant = Service(service_type='Search Engine',
                cloud='Instance2',
                url='https://www.qwant.com/')
duckduckgo = Service(service_type='Search Engine',
                     cloud='Instance3',
                     url='https://www.duckduckgo.com/')
rddg = Service(service_type='Search Engine',
               cloud='Instance4',
               url='https://duckduckgo.com/')

services = [identity, invalid, qwant, duckduckgo, rddg]
interpreter = oid.get_interpreter_from_services(services)
Session.send = requests_scope(interpreter)(Session.send)


# Only Instance2 has [200] response
#narrow_scope = "Instance1 & ((Instance3 | Instance2) & (Instance1 | Instance3)) | Instance2"
narrow_scope = "Instance2 & Instance1 & Instance2 | Instance2 & Instance1 | Instance4"
narrow_scope = "(Instance3 & Instance1) | Instance2"
#narrow_scope = "Instance2 & (Instance3 | Instance1)"
# narrow_scope = "Instance2 & Instance3 | Instance1"
# narrow_scope = "Instance3 | Instance2"
# narrow_scope = "Instance1"

scope = {'Search Engine': narrow_scope, 'identity': 'Instance0'}
headers = {'X-Scope': json.dumps(scope)}
request = Request('GET', f'{duckduckgo.url}?q=discovery', headers)

session = Session()
prepared_request = session.prepare_request(request)

##
## ATTENTION with re-directions the behaviour is really strange and
## it fails. However this will work (need more digging on 'sessions'):
##
## session_send = requests_scope(interpreter)(Session.send)
## response = session_send(session, prepared_request)
##
response = session.send(prepared_request, allow_redirects=False, verify=False)


# Exemple II basic annotation with a simple function and NO interpretation
def test_extr_scp_func(*args, **kwargs):
    return 'R|M'


def test_bool_evl_func(instance):
    return True


def test_args_xfm_func(intrepreter, endpoint,
                       *args, **kwargs):
    return args, kwargs


def test_disj_func(this, other):
    this.result = this.result + other.result
    return this


def test_conj_func(this, other):
    this.result = this.result * other.result
    return this


@OidDispatcher.scope(interpreter,
                     extr_scp_func=test_extr_scp_func,
                     bool_evl_func=test_bool_evl_func,
                     args_xfm_func=test_args_xfm_func,
                     disj_res_func=test_disj_func,
                     conj_res_func=test_conj_func)
def non_factorial(n):
    f = 1
    while(n):
        f = f * n
        n = n - 1
    return f


@OidDispatcher.scope(interpreter,
                     extr_scp_func=test_extr_scp_func,
                     bool_evl_func=test_bool_evl_func,
                     args_xfm_func=test_args_xfm_func,
                     disj_res_func=test_disj_func,
                     conj_res_func=test_conj_func)
def factorial(n):
    return 1 if n == 0 else n * factorial(n - 1)


@OidDispatcher.scope(interpreter,
                     extr_scp_func=test_extr_scp_func,
                     bool_evl_func=test_bool_evl_func,
                     args_xfm_func=test_args_xfm_func,
                     disj_res_func=test_disj_func,
                     conj_res_func=test_conj_func)
def tail_factorial(n, r = 1):
    if n <= 1:
        return r
    return tail_factorial(n - 1, n * r)

n=3

print("Non factorial")
r = non_factorial(n)

print("Factorial")
r = factorial(n)

print("Tail factorial")
r = tail_factorial(n)
