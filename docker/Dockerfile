# GlobaLeaks Unified Dockerfile
# Supports both production (remote) and testing (local) installs.
#
# Build Arguments:
#   BASE_IMAGE:     The base image for the OS (e.g., debian:bookworm-slim@sha256:...)
#   DISTRIBUTION:   The target distribution codename (e.g., bookworm)
#   INSTALL_FROM:   Installation mode. 'remote' (default) or 'local'.

ARG BASE_IMAGE=debian:bookworm-slim@sha256:36e591f228bb9b99348f584e83f16e012c33ba5cad44ef5981a1d7c0a93eca22
ARG DISTRIBUTION=bookworm
ARG INSTALL_FROM=remote

FROM ${BASE_IMAGE}

# Redeclare build arguments to make them available after FROM
ARG INSTALL_FROM=remote
ARG DISTRIBUTION=bookworm

# Install basic dependencies common to all builds
RUN apt-get update -q && \
    apt-get dist-upgrade -y && \
    apt-get install -y apt-utils wget lsb-release curl gnupg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create temporary directory for install scripts
RUN mkdir -p /tmp/install

# Copy the unified install script from the repository (build context is project root)  
COPY scripts/install.sh /tmp/install.sh

# Create directory for potential local packages
RUN mkdir -p /globaleaks/deb

# For local installation builds, copy deb packages if they exist
# Note: In CI, deb packages are built and placed in docker/deb/${DISTRIBUTION}/
# For local development, this directory exists but may be empty, which is handled in the install logic
COPY docker/deb/ /globaleaks/deb/

# Set environment for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Run the unified installation script
# The script automatically detects Docker environment and adapts its behavior
RUN echo "DEBUG: INSTALL_FROM=${INSTALL_FROM}, DISTRIBUTION=${DISTRIBUTION}" && \
    chmod +x /tmp/install.sh && \
    /tmp/install.sh && \
    # Cleanup installation files
    rm -rf /tmp/install.sh /globaleaks/deb

# Configure Docker-specific settings to disable sandboxing features (after installation)
RUN echo "NETWORK_SANDBOXING=0" >> /etc/default/globaleaks && \
    echo "APPARMOR_SANDBOXING=0" >> /etc/default/globaleaks && \
    echo "REACHABLE_VIA_WEB=0" >> /etc/default/globaleaks

EXPOSE 8080 8443

USER globaleaks

CMD ["/usr/bin/python3", "/usr/bin/globaleaks", "--working-path=/var/globaleaks/", "-n"]
