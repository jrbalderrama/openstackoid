#!/bin/bash

OID_DIR=/vagrant
OIDINTERPRETER_DIR=${OID_DIR}/oidinterpreter
OSCLI_PLUGIN_DIR=${OID_DIR}/python-openstackoidclient
OPENDEV_DIR=/opt/opendev
KEYSTONEAUTH_DIR=${OPENDEV_DIR}/keystoneauth
KEYSTONEMIDDLEWARE_DIR=${OPENDEV_DIR}/keystonemiddleware

sudo pip install -U -e ${OIDINTERPRETER_DIR}
sudo pip install -U -e ${OSCLI_PLUGIN_DIR}
sudo pip install -U -e ${KEYSTONEMIDDLEWARE_DIR}
sudo pip install -U -e ${KEYSTONEAUTH_DIR}

sudo systemctl restart devstack@*
