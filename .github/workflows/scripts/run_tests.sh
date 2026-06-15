#!/bin/bash
set -e

echo "Running setup"
sudo apt update
sudo apt install -y tor

cd $GITHUB_WORKSPACE/backend  # to install backend dependencies
python3 -mvenv env
source env/bin/activate
pip3 install --require-hashes -r requirements/requirements.txt.dev
pip3 install --require-hashes -r requirements/requirements.txt.$(lsb_release -cs)

cd $GITHUB_WORKSPACE/client  # to install frontend dependencies
npm ci
./node_modules/grunt/bin/grunt build_and_instrument

cd $GITHUB_WORKSPACE/backend && coverage run -m twisted.trial globaleaks.tests
cd $GITHUB_WORKSPACE/backend && coverage run --append ./bin/globaleaks -z -n &

sleep 3

# Running client tests locally
echo "Running client tests locally collecting code coverage"
cd $GITHUB_WORKSPACE/client && npm test

sleep 3

killall coverage --wait

sleep 3

cd $GITHUB_WORKSPACE/backend && coverage lcov -o $GITHUB_WORKSPACE/backend/lcov.info
sed -i 's|SF:globaleaks/|SF:backend/globaleaks/|g' $GITHUB_WORKSPACE/backend/lcov.info
# Keep only our own client sources (app/**) and make their paths repository-root relative.
awk -i inplace '/^SF:/{keep=sub(/^SF:(\.\/)?(dist\/)?app\//,"SF:client/app/")} keep && !/^TN:/' $GITHUB_WORKSPACE/client/cypress/coverage/lcov.info
