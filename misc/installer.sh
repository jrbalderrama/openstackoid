#!/bin/bash

PIP_OPTS="--no-deps --ignore-installed --editable"

OS_BASE_DIR=/opt/opendev
OS_BASE_PATH=${OS_BASE_DIR%%+(/)}${OS_BASE_DIR:+/}

OID_BASE_DIR="${OS_BASE_PATH}openstackoid"
KST_AUTH_DIR="${OS_BASE_PATH}keystoneauth"
KST_MIDL_DIR="${OS_BASE_PATH}keystonemiddleware"
GLC_CLNT_DIR="${OS_BASE_PATH}python-glanceclient"

for module in ${OID_BASE_DIR} ${KST_MIDL_DIR} ${KST_AUTH_DIR} ${GLC_CLNT_DIR}
do
    sudo --set-home pip install ${PIP_OPTS} $module
done
