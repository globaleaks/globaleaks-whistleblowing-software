#!/bin/bash

set -e

TARGET_DISTRIBUTION=$1

if [ -z "$TARGET_DISTRIBUTION" ]; then
    echo "Usage: $0 <target_distribution>"
    exit 1
fi

cat > docker/docker-compose.test.yml << EOF
version: '3'

services:
  globaleaks-test:
    image: globaleaks-test:${TARGET_DISTRIBUTION}
    restart: unless-stopped
    container_name: globaleaks-test-${TARGET_DISTRIBUTION}
    network_mode: bridge
    volumes:
      - globaleaks-test:/var/globaleaks
    ports:
      - "8080:8080"
      - "8443:8443"
    healthcheck:
      test: ["CMD", "curl", "-k", "-f", "https://localhost:8443"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  globaleaks-test:
EOF

echo "Created docker-compose.test.yml for $TARGET_DISTRIBUTION" 