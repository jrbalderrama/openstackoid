#!/bin/bash

SUDO_CMD="sudo --set-home"
PIP_INSTALL_OPTS="--no-deps --no-cache-dir --editable"
EASY_INSTALL_OPTS="-H None -m"

OS_BASE_DIR=/opt/stack
OID_BASE_DIR=/opt/opendev
DIST_PACKAGES_DIR=/usr/local/lib/python3.6/dist-packages

OS_BASE_PATH=${OS_BASE_DIR%%+(/)}${OS_BASE_DIR:+/}
OID_BASE_PATH=${OID_BASE_DIR%%+(/)}${OID_BASE_DIR:+/}
DIST_PACKAGES_PATH=${DIST_PACKAGES_DIR%%+(/)}${DIST_PACKAGES_DIR:+/}

OID_CORE="openstackoid"
KST_MIDL="keystonemiddleware"
KST_AUTH="keystoneauth"
OST_CLNT="python-openstackclient"

SRC_MODULES=(${KST_MIDL} ${KST_AUTH} ${OST_CLNT})
set -x

if [ -z "$1" ]
then
    ${SUDO_CMD} pip install ${PIP_INSTALL_OPTS} ${OID_BASE_PATH}${OID_CORE}
    shopt -s nullglob
    for module in ${SRC_MODULES[@]}
    do
        ${SUDO_CMD} pip uninstall --yes $module
        # required to update easy-install.pth file in dist-packages
        ${SUDO_CMD} easy_install ${EASY_INSTALL_OPTS} $module > /dev/null 2>&1
        # for alt_egg in ${DIST_PACKAGES_PATH}${module//-/_}*egg
        # do
        #     [ -d $alt_egg ] && ${SUDO_CMD} rm -rf $alt_egg
        # done
        # required in ubuntu because the package is not uninstalled
        egg="${DIST_PACKAGES_PATH}${module}.egg-link"
        [ -f $egg ] && ${SUDO_CMD} rm -f $egg
        egg_info="${OS_BASE_PATH}${module}/${module//-/_}.egg-info"
        [ -d $egg_info ] && ${SUDO_CMD} rm -rf $egg_info
        ${SUDO_CMD} pip install ${PIP_INSTALL_OPTS} ${OID_BASE_PATH}$module
    done
    shopt -u nullglob
else
    ${SUDO_CMD} pip uninstall --yes ${OID_CORE}
    ${SUDO_CMD} easy_install ${EASY_INSTALL_OPTS} ${OID_CORE} > /dev/null 2>&1
    egg="${DIST_PACKAGES_PATH}${OID_CORE}.egg-link"
    [ -f $egg ] && ${SUDO_CMD} rm -f $egg
    egg_info="${OID_BASE_PATH}${OID_CORE}/${OID_CORE}.egg-info"
    [ -d $egg_info ] && ${SUDO_CMD} rm -rf $egg_info
    for module in ${SRC_MODULES[@]}
    do
        ${SUDO_CMD} pip install ${PIP_INSTALL_OPTS} ${OS_BASE_PATH}$module
    done
fi

${SUDO_CMD} systemctl restart devstack@*
