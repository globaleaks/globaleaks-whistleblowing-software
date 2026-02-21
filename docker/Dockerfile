# GlobaLeaks Unified Dockerfile
# Supports both production (remote) and testing (local) installs.
#
# Build Arguments:
#   BASE_IMAGE:     The base image for the OS (e.g., debian:trixie-slim@sha256:...)
#   DISTRIBUTION:   The target distribution codename (e.g., trixie)
ARG BASE_IMAGE=dhi.io/debian-base:trixie-debian13@sha256:b00e3adeeac63e73ccb806b375d1b0b8bc765d75daf3dd7efc3bed15778f0a85
ARG DISTRIBUTION=trixie

FROM --platform=linux/amd64 ${BASE_IMAGE}

ADD https://deb.globaleaks.org/install.sh /tmp/install.sh

# Redeclare build arguments to make them available after FROM
ARG DISTRIBUTION=trixie

# Set environment for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

COPY files/* /tmp/

RUN apt-get update -q && \
    apt-get dist-upgrade -y && \
    apt-get install -y --no-install-recommends lsb-release passwd && \
    groupadd -r globaleaks --gid=1000 && \
    useradd -r -d /var/globaleaks -g globaleaks --uid=1000 globaleaks && \
    chmod +x /tmp/install.sh && \
    /tmp/install.sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

RUN mkdir -p /run/globaleaks && chown -R globaleaks:globaleaks /run/globaleaks

EXPOSE 8080 8443

USER 1000:1000

CMD ["/usr/bin/python3", "/usr/bin/globaleaks", "--working-path=/var/globaleaks/", "-n"]
