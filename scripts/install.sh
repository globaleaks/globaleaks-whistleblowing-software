#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

# Detect if we're running in a Docker container
DOCKER_ENV=0

# Debug: Show what we're checking
echo "Checking Docker environment..."
echo "/.dockerenv exists: $([ -f /.dockerenv ] && echo 'yes' || echo 'no')"
echo "DOCKER_CONTAINER var: '${DOCKER_CONTAINER}'"
echo "Container runtime check: $(cat /proc/1/cgroup 2>/dev/null | head -n 5)"

# Multiple detection methods for Docker environment
if [ -f /.dockerenv ] || \
   [ -n "${DOCKER_CONTAINER}" ] || \
   [ "${container}" = "docker" ] || \
   grep -q '/docker/' /proc/1/cgroup 2>/dev/null || \
   grep -q '/lxc/' /proc/1/cgroup 2>/dev/null || \
   [ -f /proc/1/cgroup ] && [ "$(cat /proc/1/cgroup | wc -l)" -eq 1 ] && grep -q '0::/$' /proc/1/cgroup; then
    DOCKER_ENV=1
    echo "Docker environment detected"
fi

# User Permission Check (skip in Docker)
if [ $DOCKER_ENV -eq 0 ] && [ ! $(id -u) = 0 ]; then
  echo "Error: GlobaLeaks install script must be run by root"
  exit 1
fi

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

  if [ $DOCKER_ENV -eq 0 ]; then
    last_command $CMD
    last_status $STATUS
  fi

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
ASSUMEYES=0
DISABLEAUTOSTART=0

DISTRO="unknown"
DISTRO_CODENAME="unknown"
if which lsb_release >/dev/null; then
  DISTRO="$(lsb_release -is)"
  DISTRO_CODENAME="$(lsb_release -cs)"
fi

# Report last executed command and its status (not needed in Docker)
if [ $DOCKER_ENV -eq 0 ]; then
  TMPDIR=$(mktemp -d)
  echo '' > $TMPDIR/last_command
  echo '' > $TMPDIR/last_status

  function last_command () {
    echo $1 > $TMPDIR/last_command
  }

  function last_status () {
    echo $1 > $TMPDIR/last_status
  }
else
  # Dummy functions for Docker environment
  function last_command () {
    true
  }

  function last_status () {
    true
  }
fi

function prompt_for_continuation () {
  if [ $DOCKER_ENV -eq 1 ] || [ $ASSUMEYES -eq 1 ]; then
    return 0  # Auto-continue in Docker or when -y is specified
  fi
  
  while true; do
    read -p "Do you wish to continue anyway? [y|n]?" yn
    case $yn in
      [Yy]*) break;;
      [Nn]*) exit 1;;
      *) echo $yn; echo "Please answer y/n.";  continue;;
    esac
  done
}

usage() {
  echo "GlobaLeaks Install Script"
  echo "Valid options:"
  echo -e " -h show the script helper"
  echo -e " -y assume yes"
  echo -e " -n disable autostart"
  echo -e " -v install a specific software version"
}

# Parse command line arguments (not in Docker environment)
if [ $DOCKER_ENV -eq 0 ]; then
  while getopts "ynv:h" opt; do
    case $opt in
      y) ASSUMEYES=1
      ;;
      n) DISABLEAUTOSTART=1
      ;;
      v) VERSION="$OPTARG"
      ;;
      h)
          usage
          exit 1
      ;;
      \?) usage
          exit 1
      ;;
    esac
  done
else
  # In Docker, assume -y (non-interactive) and -n (disable autostart)
  ASSUMEYES=1
  DISABLEAUTOSTART=1
  # Mask the service immediately to prevent any startup attempts during package installation
  systemctl mask globaleaks 2>/dev/null || true
fi

if [ $DOCKER_ENV -eq 1 ]; then
  echo "Running Docker-specific GlobaLeaks installation..."
else
  echo -e "Running the GlobaLeaks installation...\nIn case of failure please report encountered issues to the ticketing system at: https://github.com/globaleaks/globaleaks-whistleblowing-software/issues\n"
fi

echo "Detected OS: $DISTRO - $DISTRO_CODENAME"

last_command "check_distro"

if echo "$DISTRO_CODENAME" | grep -vqE "^(bookworm)|(noble)$" ; then
  echo "WARNING: The recommended up-to-date platforms are Debian 12 (Bookworm) and Ubuntu 24.04 (Noble)"
  echo "WARNING: Use one of these platforms to ensure best stability and security"

  prompt_for_continuation
fi

if [ -f /etc/systemd/system/globaleaks.service ]; then
  DO "systemctl stop globaleaks"
fi

# align apt-get cache to up-to-date state on configured repositories
DO "apt-get -y update"

if [ ! -f /etc/timezone ]; then
  echo "Etc/UTC" > /etc/timezone
fi

if [ $DOCKER_ENV -eq 1 ]; then
  DO "apt-get -y install tzdata"
  dpkg-reconfigure -f noninteractive tzdata
else
  apt-get install -y tzdata
  dpkg-reconfigure -f noninteractive tzdata
fi

DO "apt-get -y install gnupg net-tools software-properties-common wget"

# The supported platforms are experimentally more than only Ubuntu as
# publicly communicated to users.
#
# Depending on the intention of the user to proceed anyhow installing on
# a not supported distro we using the experimental package if it exists
# or bookworm as fallback.
if echo "$DISTRO_CODENAME" | grep -vqE "^(bionic|bookworm|bullseye|buster|focal|jammy|noble)$"; then
  # In case of unsupported platforms we fallback on bookworm
  echo "No packages available for the current distribution; the install script will use the bookworm repository."
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

if [ $DISABLEAUTOSTART -eq 1 ] && [ $DOCKER_ENV -eq 0 ]; then
  # Only mask for non-Docker environments (Docker already masked earlier)
  systemctl mask globaleaks
fi

if [ -d /globaleaks/deb ]; then
  DO "apt-get -y update"
  DO "apt-get -y install dpkg-dev"
  echo "Installing from locally provided debian package"
  cd /globaleaks/deb/ && dpkg-scanpackages . /dev/null | gzip -c -9 > /globaleaks/deb/Packages.gz
  if [ ! -f /etc/apt/sources.list.d/globaleaks.local.list ]; then
    echo "deb file:///globaleaks/deb/ /" >> /etc/apt/sources.list.d/globaleaks.local.list
  fi
  DO "apt -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true update"
  
  if [ $DOCKER_ENV -eq 1 ]; then
    # In Docker, use non-interactive options to avoid prompts
    DO "apt-get -y --allow-unauthenticated -o Dpkg::Options::=\"--force-confdef\" -o Dpkg::Options::=\"--force-confold\" install globaleaks"
    echo "Skipping service restart for Docker container"
  else
    DO "apt-get -y --allow-unauthenticated install globaleaks"
    # Additional safety: check if we're in a containerized environment before restarting
    if [ -f /.dockerenv ] || [ -n "${container}" ] || grep -q '/docker\|/lxc' /proc/1/cgroup 2>/dev/null; then
      echo "Container environment detected - skipping service restart"
    else
      DO "/etc/init.d/globaleaks restart"
    fi
  fi
else
  DO "apt-get update -y"
  if [[ $VERSION ]]; then
    if [ $DOCKER_ENV -eq 1 ]; then
      DO "apt-get install globaleaks=$VERSION -y -o Dpkg::Options::=\"--force-confdef\" -o Dpkg::Options::=\"--force-confold\""
    else
      DO "apt-get install globaleaks=$VERSION -y"
    fi
  else
    if [ $DOCKER_ENV -eq 1 ]; then
      DO "apt-get install globaleaks -y -o Dpkg::Options::=\"--force-confdef\" -o Dpkg::Options::=\"--force-confold\""
    else
      DO "apt-get install globaleaks -y"
    fi
  fi
  
  # For remote installation, also prevent service restart in containers
  if [ $DOCKER_ENV -eq 0 ] && ([ -f /.dockerenv ] || [ -n "${container}" ] || grep -q '/docker\|/lxc' /proc/1/cgroup 2>/dev/null); then
    echo "Container environment detected during remote installation - setting Docker mode"
    DOCKER_ENV=1
    DISABLEAUTOSTART=1
  fi
fi

if [ $DISABLEAUTOSTART -eq 1 ]; then
  if [ $DOCKER_ENV -eq 1 ]; then
    echo "GlobaLeaks Docker installation completed successfully."
    echo "The service will be started when the container runs."
  fi
  exit 0
fi

# Skip startup verification in Docker environment
if [ $DOCKER_ENV -eq 1 ]; then
  echo "GlobaLeaks Docker installation completed successfully."
  echo "The service will be started when the container runs."
  exit 0
fi

# Set the script to its success condition
last_command "startup"
last_status "0"

sleep 5

i=0
while [ $i -lt 30 ]
do
  X=$(netstat -tln | grep ":8443")
  if [ $? -eq 0 ]; then
    #SUCCESS
    echo "GlobaLeaks setup completed."
    TOR=$(gl-admin getvar onionservice)
    echo "To proceed with the configuration you could now access the platform wizard at:"
    echo "+ http://$TOR (via the Tor Browser)"
    echo "+ https://127.0.0.1:8443"
    echo "+ https://0.0.0.0"
    echo "We recommend you to to perform the wizard by using Tor address or on localhost via a VPN."
    exit 0
  fi
  i=$[$i+1]
  sleep 1
done

#ERROR
echo "Ouch! The installation is complete but GlobaLeaks failed to start."
netstat -tln
cat /var/globaleaks/log/globaleaks.log
last_status "1"
exit 1
