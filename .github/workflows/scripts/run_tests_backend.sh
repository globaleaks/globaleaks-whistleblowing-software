#!/bin/bash

backend_test_failed=0

setupBackend() {
  cd $GITHUB_WORKSPACE/backend  # to install backend dependencies
  pip3 install -r requirements/requirements-$(lsb_release -cs).txt
}

setupClient() {
  cd $GITHUB_WORKSPACE/client  # to install frontend dependencies
  npm install -d
  ./node_modules/grunt/bin/grunt build_and_instrument
}

echo "Running setup"
sudo apt-get update
sudo apt-get install -y libfuse2 tor
npm install -g grunt grunt-cli
pip install coverage

setupBackend
setupClient

# Running backend tests
echo "Running backend tests"
cd $GITHUB_WORKSPACE/backend && coverage run setup.py test
if [ $? -ne 0 ]; then
  backend_test_failed=1
fi

cd $GITHUB_WORKSPACE/backend && coverage xml
bash <(curl -Ls https://coverage.codacy.com/get.sh) report -l Python -r $GITHUB_WORKSPACE/backend/coverage.xml

if [ $backend_test_failed -eq 1 ]; then
  echo "Backend unit tests: FAILED"
  exit 1
else
  echo "Backend unit tests: PASSED"
  exit 0
fi
