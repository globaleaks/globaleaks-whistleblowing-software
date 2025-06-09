#!/bin/bash

set -e

TARGET_DISTRIBUTION=$1

if [ -z "$TARGET_DISTRIBUTION" ]; then
    echo "Usage: $0 <target_distribution>"
    exit 1
fi

# Map distributions to their corresponding Docker base images
case $TARGET_DISTRIBUTION in
    "bookworm")
        BASE_IMAGE="debian:bookworm-slim"
        ;;
    "noble")
        BASE_IMAGE="ubuntu:24.04"
        ;;
    "jammy")
        BASE_IMAGE="ubuntu:22.04"
        ;;
    "focal")
        BASE_IMAGE="ubuntu:20.04"
        ;;
    *)
        echo "Unsupported distribution: $TARGET_DISTRIBUTION"
        echo "Supported distributions: bookworm, noble, jammy, focal"
        exit 1
        ;;
esac

# Create the test Dockerfile
cat > docker/Dockerfile.test << EOF
FROM ${BASE_IMAGE}

# Install basic dependencies
RUN apt-get update -q && \\
    apt-get dist-upgrade -y && \\
    apt-get install -y apt-utils wget lsb-release curl gnupg && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*

# Copy the local .deb files
COPY deb/ /globaleaks/deb/

# Copy and run the install script
COPY install.sh /tmp/install.sh
RUN chmod +x /tmp/install.sh && \\
    /tmp/install.sh -y -n

# Expose the ports
EXPOSE 8080 8443

# Switch to globaleaks user
USER globaleaks

# Start the service
CMD ["/usr/bin/python3", "/usr/bin/globaleaks", "--working-path=/var/globaleaks/", "-n"]
EOF

echo "Created Dockerfile.test for $TARGET_DISTRIBUTION using base image: $BASE_IMAGE" 