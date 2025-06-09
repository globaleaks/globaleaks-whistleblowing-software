#!/bin/bash

set -e

# Default values
DISTRIBUTION="bookworm"
CLEANUP=1
VERBOSE=0

usage() {
  echo "GlobaLeaks Docker Test Script"
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -d DISTRIBUTION  Target distribution (bookworm, noble, jammy, focal)"
  echo "  -n               No cleanup (leave containers running)"
  echo "  -v               Verbose output"
  echo "  -h               Show this help"
}

while getopts "d:nvh" opt; do
  case $opt in
    d) DISTRIBUTION="$OPTARG"
    ;;
    n) CLEANUP=0
    ;;
    v) VERBOSE=1
    ;;
    h)
        usage
        exit 0
    ;;
    \?) usage
        exit 1
    ;;
  esac
done

# Validate distribution
case $DISTRIBUTION in
    "bookworm"|"noble"|"jammy"|"focal")
        echo "Testing with distribution: $DISTRIBUTION"
        ;;
    *)
        echo "Error: Unsupported distribution: $DISTRIBUTION"
        echo "Supported: bookworm, noble, jammy, focal"
        exit 1
        ;;
esac

# Set verbose mode
if [ $VERBOSE -eq 1 ]; then
    set -x
fi

echo "=== GlobaLeaks Docker Testing Script ==="
echo "Distribution: $DISTRIBUTION"
echo "Cleanup: $([ $CLEANUP -eq 1 ] && echo 'Yes' || echo 'No')"
echo

# Step 1: Build Debian package
echo "Step 1: Building Debian package..."
./scripts/build.sh -d $DISTRIBUTION -n -l

# Check if build was successful
if [ ! -d "build/$DISTRIBUTION" ]; then
    echo "Error: Build directory not found"
    exit 1
fi

DEB_FILE=$(find build/$DISTRIBUTION -name "*.deb" | head -n 1)
if [ -z "$DEB_FILE" ]; then
    echo "Error: No .deb file found in build/$DISTRIBUTION"
    exit 1
fi

echo "Built package: $DEB_FILE"

# Step 2: Set up Docker environment
echo "Step 2: Setting up Docker environment..."
mkdir -p docker/deb
cp build/$DISTRIBUTION/*.deb docker/deb/
cp scripts/install.sh docker/

# Create test Dockerfile
./.github/workflows/scripts/create_test_dockerfile.sh $DISTRIBUTION

# Step 3: Build Docker image
echo "Step 3: Building Docker image..."
cd docker
docker build -f Dockerfile.test -t globaleaks-test:$DISTRIBUTION .

# Step 4: Set up and start container
echo "Step 4: Starting Docker container..."
./.github/workflows/scripts/setup_test_compose.sh $DISTRIBUTION
docker-compose -f docker-compose.test.yml up -d

# Step 5: Wait for service
echo "Step 5: Waiting for GlobaLeaks to start..."
timeout 120 bash -c 'until curl -k https://localhost:8443 2>/dev/null; do echo "Waiting..."; sleep 5; done' || {
    echo "Error: Service failed to start within 120 seconds"
    echo "Container logs:"
    docker-compose -f docker-compose.test.yml logs
    if [ $CLEANUP -eq 1 ]; then
        docker-compose -f docker-compose.test.yml down
    fi
    exit 1
}

echo "GlobaLeaks is ready!"

# Step 6: Run Cypress tests
echo "Step 6: Running Cypress tests..."
cd ../client

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install -d
fi

# Run Cypress tests
echo "Starting Cypress tests..."
npx cypress run --browser chrome --config baseUrl=https://localhost:8443,chromeWebSecurity=false

CYPRESS_EXIT_CODE=$?

# Step 7: Cleanup
cd ../docker
if [ $CLEANUP -eq 1 ]; then
    echo "Step 7: Cleaning up..."
    docker-compose -f docker-compose.test.yml down
    
    # Clean up generated files
    rm -f Dockerfile.test docker-compose.test.yml install.sh
    rm -rf deb/
else
    echo "Step 7: Skipping cleanup (containers left running)"
    echo "To stop containers manually: cd docker && docker-compose -f docker-compose.test.yml down"
fi

# Report results
echo
echo "=== Test Results ==="
if [ $CYPRESS_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed (exit code: $CYPRESS_EXIT_CODE)"
fi

echo "Distribution: $DISTRIBUTION"
echo "GlobaLeaks URL: https://localhost:8443"

exit $CYPRESS_EXIT_CODE 