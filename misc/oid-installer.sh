#!/bin/bash

GIT_TMP=/tmp
GIT_BASE=https://github.com/jrbalderrama
BRANCH=oid/stein

sudo pip install git+${GIT_BASE}/keystonemiddleware@${BRANCH}
sudo pip install git+${GIT_BASE}/keystoneauth@${BRANCH}
git clone --branch ${BRANCH} ${GIT_BASE}/openstackoid.git ${GIT_TMP}/openstackoid
sudo pip install --upgrade --editable ${GIT_TMP}/openstackoid
sudo systemctl restart devstack@*
