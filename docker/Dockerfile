# GlobaLeaks Unified Dockerfile
# Supports both production (remote) and testing (local) installs.
#
# Build Arguments:
#   BASE_IMAGE:     The base image for the OS (e.g., debian:bookworm-slim)
#   DISTRIBUTION:   The target distribution codename (e.g., bookworm)
#   INSTALL_FROM:   Installation mode. 'remote' (default) or 'local'.

ARG BASE_IMAGE=debian:bookworm-slim
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

# For local installation, the build context must contain:
# ./deb/${DISTRIBUTION}/*.deb  (The built packages)
# ./install-docker.sh         (The Docker-specific install script)
# For remote installation, the build context must contain:
# ./install-globaleaks.sh     (The GlobaLeaks install script)
COPY deb/${DISTRIBUTION} /globaleaks/deb/
COPY install-docker.sh /tmp/install-docker.sh
COPY ../scripts/install.sh /tmp/install-globaleaks.sh

# Set environment for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Run the appropriate installation method based on INSTALL_FROM argument
RUN echo "DEBUG: INSTALL_FROM=${INSTALL_FROM}, DISTRIBUTION=${DISTRIBUTION}" && \
    if [ "${INSTALL_FROM}" = "local" ]; then \
        echo "--- Performing local installation ---"; \
        chmod +x /tmp/install-docker.sh && \
        /tmp/install-docker.sh; \
    else \
        echo "--- Performing remote installation ---"; \
        chmod +x /tmp/install-globaleaks.sh && \
        /tmp/install-globaleaks.sh -y -n; \
    fi && \
    # Cleanup installation files
    rm -rf /tmp/install-docker.sh /tmp/install-globaleaks.sh /globaleaks/deb

# Configure Docker-specific settings to disable sandboxing features (after installation)
RUN echo "NETWORK_SANDBOXING=0" >> /etc/default/globaleaks && \
    echo "APPARMOR_SANDBOXING=0" >> /etc/default/globaleaks && \
    echo "REACHABLE_VIA_WEB=0" >> /etc/default/globaleaks

EXPOSE 8080 8443

USER globaleaks

CMD ["/usr/bin/python3", "/usr/bin/globaleaks", "--working-path=/var/globaleaks/", "-n"]
