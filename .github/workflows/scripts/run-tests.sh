#!/bin/bash

set -e

setupClient() {
  cd  $GITHUB_WORKSPACE/client  # to install frontend dependencies
  npm install -d
  ./node_modules/grunt/bin/grunt build_and_instrument
}

setupBackend() {
  cd  $GITHUB_WORKSPACE/backend  # to install backend dependencies
  pip3 install -r requirements/requirements-$(lsb_release -cs).txt
}

echo "Running setup"
sudo apt-get update
sudo apt-get install -y tor
npm install -g grunt grunt-cli
pip install coverage
setupClient
setupBackend

echo "Running backend unit tests"
cd  $GITHUB_WORKSPACE/backend && coverage run setup.py test

$GITHUB_WORKSPACE/backend/bin/globaleaks -z
sleep 5

echo "Running BrowserTesting locally collecting code coverage"
cd  $GITHUB_WORKSPACE/client && npm test

cd  $GITHUB_WORKSPACE/backend && coverage xml
bash <(curl -Ls https://coverage.codacy.com/get.sh) report -l Python -r  $GITHUB_WORKSPACE/backend/coverage.xml
bash <(curl -Ls https://coverage.codacy.com/get.sh) report -l TypeScript -r  $GITHUB_WORKSPACE/client/cypress/coverage/lcov.info
bash <(curl -Ls https://coverage.codacy.com/get.sh) final
