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

from openstackoid.interpreter import Service
from openstackoid.dispatcher import OidDispatcher

import openstackoid.interpreter as oid


logger = logging.getLogger(__name__)
logging.basicConfig(format='\t%(levelname)s\t: %(message)s')
logger.setLevel(logging.DEBUG)


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

narrow_scope = "Instance1 & ((Instance3 | Instance2) & (Instance1 | Instance3)) | Instance2"
#narrow_scope = "Instance2 & Instance1 & Instance2 | Instance2 & Instance1 | Instance0"
#narrow_scope = "Instance2 & (Instance3 | Instance1)"
#narrow_scope = "Instance3 | Instance2"
#narrow_scope = "Instance1"

scope = {'Search Engine': narrow_scope, 'identity': 'Instance1'}
headers = {'X-Scope': json.dumps(scope)}
request = Request('GET', f'https://www.duckduckgo.com/?q=discovery', headers)
services = [identity, invalid, qwant, duckduckgo]
interpreter = oid.get_interpreter_from_services(services)
session = Session()
prepared_request = session.prepare_request(request)
response = OidDispatcher[Response].requests_scope()(interpreter, session, prepared_request)
