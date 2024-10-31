#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

# User Permission Check
if [ ! $(id -u) = 0 ]; then
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

  last_command $CMD
  last_status $STATUS

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

# Report last executed command and its status
TMPDIR=$(mktemp -d)
echo '' > $TMPDIR/last_command
echo '' > $TMPDIR/last_status

function last_command () {
  echo $1 > $TMPDIR/last_command
}

function last_status () {
  echo $1 > $TMPDIR/last_status
}

function prompt_for_continuation () {
  if [ $ASSUMEYES -eq 0 ]; then
    while true; do
      read -p "Do you wish to continue anyway? [y|n]?" yn
      case $yn in
        [Yy]*) break;;
        [Nn]*) exit 1;;
        *) echo $yn; echo "Please answer y/n.";  continue;;
      esac
    done
  fi
}

usage() {
  echo "GlobaLeaks Install Script"
  echo "Valid options:"
  echo -e " -h show the script helper"
  echo -e " -y assume yes"
  echo -e " -n disable autostart"
  echo -e " -v install a specific software version"
}

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

echo -e "Running the GlobaLeaks installation...\nIn case of failure please report encountered issues to the ticketing system at: https://github.com/globaleaks/globaleaks-whistleblowing-software/issues\n"

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

apt-get install -y tzdata
dpkg-reconfigure -f noninteractive tzdata

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

echo "Adding GlobaLeaks PGP key to trusted APT keys"
wget -qO- https://deb.globaleaks.org/globaleaks.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/globaleaks.gpg

echo "Updating GlobaLeaks apt source.list in /etc/apt/sources.list.d/globaleaks.list ..."
echo "deb [signed-by=/etc/apt/trusted.gpg.d/globaleaks.gpg] http://deb.globaleaks.org $DISTRO_CODENAME/" > /etc/apt/sources.list.d/globaleaks.list

if [ $DISABLEAUTOSTART -eq 1 ]; then
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
  DO "apt-get -y --allow-unauthenticated install globaleaks"
  DO "/etc/init.d/globaleaks restart"
else
  DO "apt-get update -y"
  if [[ $VERSION ]]; then
    DO "apt-get install globaleaks=$VERSION -y"
  else
    DO "apt-get install globaleaks -y"
  fi
fi

if [ $DISABLEAUTOSTART -eq 1 ]; then
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
