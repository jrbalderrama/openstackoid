#!/bin/bash

OID_BASE_DIR=/vagrant
OS_BASE_DIR=/opt/opendev
OS_BASE_PATH=${OS_BASE_DIR%%+(/)}${OS_BASE_DIR:+/}

KST_AUTH_DIR="${OS_BASE_PATH}keystoneauth"
KST_MIDL_DIR="${OS_BASE_PATH}keystonemiddleware"

sudo --set-home pip install --no-deps --ignore-installed --editable ${OID_BASE_DIR}
sudo --set-home pip install --no-deps --ignore-installed --editable ${KST_MIDL_DIR}
sudo --set-home pip install --no-deps --ignore-installed --editable ${KST_AUTH_DIR}

sudo systemctl restart devstack@*
