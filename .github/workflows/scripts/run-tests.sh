#!/bin/bash

backend_test_failed=0
browser_test_failed=0

setupClient() {
  cd $GITHUB_WORKSPACE/client  # to install frontend dependencies
  npm install -d
  ./node_modules/grunt/bin/grunt build_and_instrument
}

setupBackend() {
  cd $GITHUB_WORKSPACE/backend  # to install backend dependencies
  pip3 install -r requirements/requirements-$(lsb_release -cs).txt
}

echo "Running setup"
sudo apt-get update
sudo apt-get install -y tor
npm install -g grunt grunt-cli
pip install coverage
setupClient
setupBackend

# Running Backend Unit Tests
echo "Running backend unit tests"
cd $GITHUB_WORKSPACE/backend && coverage run setup.py test
if [ $? -ne 0 ]; then
  echo "Backend unit tests failed!"
  backend_test_failed=1
else
  echo "Backend unit tests succeeded!"
fi

$GITHUB_WORKSPACE/backend/bin/globaleaks -z
sleep 5

# Running BrowserTesting Locally
echo "Running BrowserTesting locally collecting code coverage"
cd $GITHUB_WORKSPACE/client && npm test
if [ $? -ne 0 ]; then
  echo "Browser tests failed!"
  browser_test_failed=1
else
  echo "Browser tests succeeded!"
fi

cd $GITHUB_WORKSPACE/backend && coverage xml
bash <(curl -Ls https://coverage.codacy.com/get.sh) report -l Python -r $GITHUB_WORKSPACE/backend/coverage.xml
bash <(curl -Ls https://coverage.codacy.com/get.sh) report -l TypeScript -r $GITHUB_WORKSPACE/client/cypress/coverage/lcov.info

# At the end, check if any of the critical tests failed
echo "Test Results Summary:"
if [ $backend_test_failed -eq 1 ]; then
  echo "  - Backend unit tests: FAILED"
else
  echo "  - Backend unit tests: PASSED"
fi

if [ $browser_test_failed -eq 1 ]; then
  echo "  - Browser tests: FAILED"
else
  echo "  - Browser tests: PASSED"
fi

# Final exit based on the test results
if [ $backend_test_failed -eq 1 ] || [ $browser_test_failed -eq 1 ]; then
  echo "One or both critical tests failed."
  exit 1  # Exit with failure if either critical test failed
else
  echo "Script completed successfully."
  exit 0  # Exit successfully if no critical test failed
fi
