#!/usr/bin/env bash

set -e

# Define supported distros as: name|base_image
distros=(
  "bookworm|debian:bookworm-slim@sha256:36e591f228bb9b99348f584e83f16e012c33ba5cad44ef5981a1d7c0a93eca22"
  "bullseye|debian:bullseye-slim@sha256:b5f9bc44bdfbd9d551dfdd432607cbc6bb5d9d6dea726a1191797d7749166973"
  "noble|ubuntu:24.04@sha256:440dcf6a5640b2ae5c77724e68787a906afb8ddee98bf86db94eea8528c2c076"
  "jammy|ubuntu:22.04@sha256:3c61d3759c2639d4b836d32a2d3c83fa0214e36f195a3421018dbaaf79cbe37f"
  "focal|ubuntu:20.04@sha256:8feb4d8ca5354def3d8fce243717141ce31e2c428701f6682bd2fafe15388214"
)

base_port=8443
distro_names=()

# Compose usage block
cat > docker-compose.yml <<EOF
# Usage Examples:
#   docker-compose up -d --build                                 # Test all distros
#   docker-compose --profile globaleaks-<distro> up -d --build   # Test a single distro
#   docker-compose --profile globaleaks-all up -d --build        # Test all distros

version: '3.9'

services:
EOF

# Compose service blocks
for i in "${!distros[@]}"; do
  IFS="|" read -r name base_image <<< "${distros[$i]}"
  port=$((base_port + i))
  distro_names+=("$name")

  service_name="globaleaks-${name}"
  image_name="globaleaks:${name}"
  container_name="globaleaks-${name}"

  cat >> docker-compose.yml <<EOF

  ${service_name}:
    environment:
      DISTRIBUTION: ${name}
    build:
      context: ..
      dockerfile: docker/Dockerfile
      args:
        INSTALL_FROM: local
        DISTRIBUTION: ${name}
        BASE_IMAGE: ${base_image}
    image: ${image_name}
    container_name: ${container_name}
    ports:
      - "${port}:8443"
    healthcheck:
      test: ["CMD", "curl", "-k", "-f", "https://localhost:8443/api/health"]
      interval: 30s
      timeout: 5s
      retries: 12
      start_period: 60s
    profiles:
      - testing-${name}
      - testing-all
EOF
done

echo "docker-compose.yml generated for distros: ${distro_names[*]}"
