#!/bin/bash

DEVSTACK_ONE=http://192.168.144.247
REDIRECT_SERVER=http://localhost:9000

set -x
## get token with auth.json file as configuration
## token is located in headers
TOKEN=$(http --headers \
             ${DEVSTACK_ONE}/identity/v3/auth/tokens \
             @auth.json | sed '/X-Subject-Token/!d;s/.* //')

## cleaning new lines
TOKEN=${TOKEN//[$'\t\r\n']} && TOKEN=${TOKEN%%*( )}

# set -x

# ## test using direct API calls
# http ${DEVSTACK_ONE}/image/v2/images \
#      X-Auth-Token:${TOKEN} \
#      X-Identity-Region:InstanceOne \
#      X-Identity-Url:${DEVSTACK_ONE}/identity

# SCOPE="{\"identity\":\"CloudOne\"}"

SCOPE="{\"image\":\"CloudOne\"}"

http --verbose ${DEVSTACK_ONE}/image/v2/images \
     X-Auth-Token:${TOKEN} \
     X-Identity-Region:CloudOne \
     X-Scope:${SCOPE} \
     X-Identity-Url:${DEVSTACK_ONE}/identity

# ## test using glance client call
# glance --verbose -d --os-auth-token=${TOKEN} \
#        --os-image-url=${DEVSTACK_ONE}/image \
#        image-list

# ## test using direct API calls with redirects (verbose)
# http --verbose --follow --all \
#      ${REDIRECT_SERVER}/image/v2/images \
#      X-Auth-Token:${TOKEN} \
#      X-Identity-Region:InstanceOne \
#      X-Identity-Url:${DEVSTACK_ONE}/identity
#
# ## test using glance client call with redirects (verbose)
# #--os-image-api-version=2
# glance --debug --verbose \
#        --os-auth-token=${TOKEN} \
#        --os-image-url=${REDIRECT_SERVER}/image \
#        image-list
#
# ## get token with redirects
# http --verbose --follow --all \
#      ${REDIRECT_SERVER}/identity/v3/auth/tokens @auth.json

#nova --os-token=${TOKEN} flavor-list

# -L -i
#python -m json.tool <<< $(curl -s -g -X GET -H Content-Type:application/octet-stream -H X-Auth-Token:$TOKEN -H User-Agent:python-glanceclient -H Accept-Encoding:gzip,deflate -H Accept:*/* -H Connection:keep-alive http://192.168.141.245/image/v2/images)







#--os-image-url=${KEYSTON_ONE}
#--os-project-domain-id=default
#--os-project-name=admin
#--os-username=admin
#--os-password=admin
# export OS_PROJECT_NAME=admin
# export OS_PASSWORD=admin
# export OS_USERNAME=admin
# export OS_AUTH_URL=http://192.168.141.245/identity/v3
# export OS_AUTH_TOKEN=$TOKEN

# OS_USER_DOMAIN_ID=default

# OS_PROJECT_DOMAIN_ID=default
# OS_REGION_NAME=InstanceOne

# OS_IDENTITY_API_VERSION=3
# OS_TENANT_NAME=admin
# OS_AUTH_TYPE=password

# OS_VOLUME_API_VERSION=3
