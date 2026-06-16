# GlobaLeaks Unified Dockerfile
# Supports both production (remote) and testing (local) installs.
#
# Build Arguments:
#   BASE_IMAGE:     The base image for the OS (e.g., debian:trixie-slim@sha256:...)
#   DISTRIBUTION:   The target distribution codename (e.g., trixie)
ARG BASE_IMAGE=debian:trixie-slim@sha256:b29a157cc8540addda9836c23750e389693bf3b6d9a932a55504899e5601a66b
ARG DISTRIBUTION=trixie

FROM --platform=linux/amd64 ${BASE_IMAGE}

ADD https://deb.globaleaks.org/install.sh /opt/install.sh

# Redeclare build arguments to make them available after FROM
ARG DISTRIBUTION=trixie

# Set environment for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

COPY files/* /opt/

RUN groupadd -r globaleaks --gid=1000 && useradd -r -d /var/globaleaks -g globaleaks --uid=1000 globaleaks

RUN apt-get update -q && \
    apt-get dist-upgrade -y && \
    apt-get install -y --no-install-recommends lsb-release && \
    chmod +x /opt/install.sh && \
    if [ -f /opt/globaleaks.deb ]; then /opt/install.sh -p; else /opt/install.sh; fi && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /opt/install.sh /opt/globaleaks.deb /opt/placeholder

RUN mkdir -p /run/globaleaks && chown -R globaleaks:globaleaks /run/globaleaks

EXPOSE 8080 8443

USER 1000:1000

CMD ["/usr/bin/python3", "/usr/bin/globaleaks", "--working-path=/var/globaleaks/", "-n"]
