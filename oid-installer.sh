File Edit Options Buffers Tools Sh-Script Help
#!/bin/bash

OID_DIR=/vagrant
OIDINTERPRETER_DIR=${OID_DIR}/oidinterpreter
OPENDEV_DIR=/opt/opendev
KEYSTONEAUTH_DIR=${OPENDEV_DIR}/keystoneauth
KEYSTONEMIDDLEWARE=${OPENDEV_DIR}/keystonemiddleware

sudo pip install -U -e ${OIDINTERPRETER_DIR}
sudo pip install -U -e ${KEYSTONEMIDDLEWARE}
sudo pip install -U -e ${KEYSTONEAUTH_DIR}

sudo systemctl restart devstack@*
