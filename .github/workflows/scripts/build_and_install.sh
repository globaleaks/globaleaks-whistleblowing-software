#!/bin/bash -x
set -e

echo "Running Build & Install"
distro="$(lsb_release -cs)"

cd /build/globaleaks-whistleblowing-software

sudo apt-get -y update

sudo apt-get -y install curl git debhelper devscripts dh-apparmor dh-python python3-all python3-pip python3-setuptools python3-sphinx

curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get update
sudo apt-get install -y nodejs

sed -ie 's/key_bits = 2048/key_bits = 512/g' backend/globaleaks/settings.py
sed -ie 's/csr_sign_bits = 512/csr_sign_bits = 256/g' backend/globaleaks/settings.py
rm debian/control backend/requirements.txt

cat >debian/changelog <<EOL
globaleaks (6.6.6) stable; urgency=medium

  * GlobaLeaks CI package

 -- GlobaLeaks software signing key <info@globaleaks.org>  Wed, 30 May 2018 14:19:43 +0200
EOL

cp debian/controlX/control.$distro debian/control
cp backend/requirements/requirements-$distro.txt backend/requirements.txt

cd client && npm install -d && ./node_modules/grunt/bin/grunt build && cd ..

echo "NETWORK_SANDBOXING=0" > debian/default
echo "APPARMOR_SANDBOXING=0" >> debian/default

debuild -i -us -uc -b

sudo mkdir -p /globaleaks/deb/
sudo cp ../globaleaks*deb /globaleaks/deb/

sudo ./scripts/install.sh -y
