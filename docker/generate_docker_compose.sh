#!/usr/bin/env bash
set -e

# Define supported distros as: name|base_image
distros=(
  "bionic|ubuntu:18.04@sha256:152dc042452c496007f07ca9127571cb9c29697f42acbfad72324b2bb2e43c98"
  "bookworm|debian:bookworm-slim@sha256:60eac759739651111db372c07be67863818726f754804b8707c90979bda511df"
  "jammy|ubuntu:22.04@sha256:4f838adc7181d9039ac795a7d0aba05a9bd9ecd480d294483169c5def983b64d"
  "noble|ubuntu:24.04@sha256:786a8b558f7be160c6c8c4a54f9a57274f3b4fb1491cf65146521ae77ff1dc54"
  "resolute|ubuntu:26.04@sha256:53958ec7b67c2c9355df922dd08dbf0360611f8c3cdb656875e81873db9ffdba"
  "trixie|debian:trixie-slim@sha256:28de0877c2189802884ccd20f15ee41c203573bd87bb6b883f5f46362d24c5c2"
)

# Read distro parameter
selected_distro="$1"
if [ -z "$selected_distro" ]; then
  echo "Usage: $0 <distro-name>"
  exit 1
fi

# Find matching distro
match=""
for entry in "${distros[@]}"; do
  IFS="|" read -r name base_image <<< "$entry"
  if [ "$name" == "$selected_distro" ]; then
    match="$entry"
    break
  fi
done

if [ -z "$match" ]; then
  echo "Error: unknown distro '$selected_distro'"
  exit 1
fi

IFS="|" read -r name base_image <<< "$match"

# Output docker-compose YAML
cat <<EOF
version: '3.9'

services:
  globaleaks:
    environment:
      DISTRIBUTION: ${name}
    build:
      context: .
      args:
        BASE_IMAGE: ${base_image}
        DISTRIBUTION: ${name}
    restart: unless-stopped
    container_name: globaleaks
    network_mode: bridge
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /run/globaleaks:mode=1777
      - /tmp:mode=1777
    volumes:
      - globaleaks:/var/globaleaks:rw
    ports:
      - 80:8080
      - 443:8443
      - 8080:8080
      - 8443:8443
    healthcheck:
      test: ["CMD", "curl", "-k", "-f", "https://localhost:8443/api/health"]
      interval: 30s
      timeout: 5s
      retries: 12
      start_period: 60s

volumes:
  globaleaks: {}
EOF

