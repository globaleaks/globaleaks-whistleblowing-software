#!/usr/bin/env bash
set -e

# Define supported distros as: name|base_image
distros=(
  "bionic|ubuntu:18.04@sha256:152dc042452c496007f07ca9127571cb9c29697f42acbfad72324b2bb2e43c98"
  "bookworm|debian:bookworm-slim@sha256:36e591f228bb9b99348f584e83f16e012c33ba5cad44ef5981a1d7c0a93eca22"
  "bullseye|debian:bullseye-slim@sha256:b5f9bc44bdfbd9d551dfdd432607cbc6bb5d9d6dea726a1191797d7749166973"
  "focal|ubuntu:20.04@sha256:8feb4d8ca5354def3d8fce243717141ce31e2c428701f6682bd2fafe15388214"
  "jammy|ubuntu:22.04@sha256:3c61d3759c2639d4b836d32a2d3c83fa0214e36f195a3421018dbaaf79cbe37f"
  "noble|ubuntu:24.04@sha256:440dcf6a5640b2ae5c77724e68787a906afb8ddee98bf86db94eea8528c2c076"
  "trixie|debian:trixie-slim@sha256:f2306da7a8fb6440535937baed0ce0018736742d6dc5beec9d6a31355b259726"
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

