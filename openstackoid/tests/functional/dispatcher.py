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
from openstackoid.dispatcher import requests_scope

import openstackoid.interpreter as oid


logger = logging.getLogger(__name__)
logging.basicConfig(format='\t%(levelname)s\t: %(message)s')
#logger.setLevel(logging.DEBUG)
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
narrow_scope = "Instance2 & Instance1 & Instance2 | Instance2 & Instance1 | Instance0"
narrow_scope = "(Instance3 & Instance1) | Instance2"
narrow_scope = "Instance2 & (Instance3 | Instance1)"
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
