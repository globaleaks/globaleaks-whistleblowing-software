#!/bin/bash
# Docker-specific GlobaLeaks installation script
# Based on the original install.sh but adapted for containers

set -e

function DO () {
  CMD="$1"

  if [ -z "$2" ]; then
    EXPECTED_RET=0
  else
    EXPECTED_RET=$2
  fi

  echo -n "Running: \"$CMD\"... "
  eval $CMD &>${LOGFILE}

  STATUS=$?

  if [ "$STATUS" -eq "$EXPECTED_RET" ]; then
    echo "SUCCESS"
  else
    echo "FAIL"
    echo "Ouch! The installation failed."
    echo "COMBINED STDOUT/STDERR OUTPUT OF FAILED COMMAND:"
    cat ${LOGFILE}
    exit 1
  fi
}

LOGFILE="./install.log"
DISTRO="unknown"
DISTRO_CODENAME="unknown"

if which lsb_release >/dev/null; then
  DISTRO="$(lsb_release -is)"
  DISTRO_CODENAME="$(lsb_release -cs)"
fi

echo "Running Docker-specific GlobaLeaks installation..."
echo "Detected OS: $DISTRO - $DISTRO_CODENAME"

# Align apt-get cache to up-to-date state on configured repositories
DO "apt-get -y update"

if [ ! -f /etc/timezone ]; then
  echo "Etc/UTC" > /etc/timezone
fi

DO "apt-get -y install tzdata"
dpkg-reconfigure -f noninteractive tzdata

DO "apt-get -y install gnupg net-tools software-properties-common wget"

# Handle unsupported distributions
if echo "$DISTRO_CODENAME" | grep -vqE "^(bionic|bookworm|bullseye|buster|focal|jammy|noble)$"; then
  echo "No packages available for the current distribution; using bookworm repository."
  DISTRO="Debian"
  DISTRO_CODENAME="bookworm"
fi

# Add GlobaLeaks repository (only if not installing from local packages)
if [ ! -d /globaleaks/deb ]; then
  echo "Adding GlobaLeaks PGP key to trusted APT keys"
  wget -qO- https://deb.globaleaks.org/globaleaks.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/globaleaks.gpg

  echo "Updating GlobaLeaks apt source.list in /etc/apt/sources.list.d/globaleaks.list ..."
  echo "deb [signed-by=/etc/apt/trusted.gpg.d/globaleaks.gpg] http://deb.globaleaks.org $DISTRO_CODENAME/" > /etc/apt/sources.list.d/globaleaks.list
fi

# Mask the service to prevent automatic startup
systemctl mask globaleaks

# Install from local packages if available
if [ -d /globaleaks/deb ]; then
  DO "apt-get -y update"
  DO "apt-get -y install dpkg-dev"
  echo "Installing from locally provided debian package"
  cd /globaleaks/deb/ && dpkg-scanpackages . /dev/null | gzip -c -9 > /globaleaks/deb/Packages.gz
  if [ ! -f /etc/apt/sources.list.d/globaleaks.local.list ]; then
    echo "deb file:///globaleaks/deb/ /" >> /etc/apt/sources.list.d/globaleaks.local.list
  fi
  DO "apt -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true update"
  DO "apt-get -y --allow-unauthenticated install globaleaks"
  
  # Skip service restart for Docker - service will be started via CMD
  echo "Skipping service restart for Docker container"
else
  DO "apt-get update -y"
  DO "apt-get install globaleaks -y"
fi

echo "GlobaLeaks Docker installation completed successfully."
echo "The service will be started when the container runs." 