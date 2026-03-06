#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

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

  if [ "$STATUS" -ne "$EXPECTED_RET" ]; then
    echo "FAIL"
    echo "Ouch! The installation failed."
    echo "COMBINED STDOUT/STDERR OUTPUT OF FAILED COMMAND:"
    cat ${LOGFILE}
    exit 1
  fi
}

HAS_SYSTEMD() {
  [ -d /run/systemd/system ]
}

LOGFILE="./install.log"
ASSUMEYES=0

DISTRO="unknown"
DISTRO_CODENAME="unknown"
if which lsb_release >/dev/null; then
  DISTRO="$(lsb_release -is)"
  DISTRO_CODENAME="$(lsb_release -cs)"
fi

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
  if [ $ASSUMEYES -eq 1 ]; then
    return 0
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

while getopts "ynv:h" opt; do
  case $opt in
    y) ASSUMEYES=1
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

if echo "$DISTRO_CODENAME" | grep -vqE "^(trixie)|(noble)$" ; then
  echo "WARNING: The recommended up-to-date platforms are Debian 13 (Trixie) and Ubuntu 24.04 (Noble)"
  echo "WARNING: Use one of these platforms to ensure best stability and security"

  prompt_for_continuation
fi

# align apt cache to up-to-date state on configured repositories
DO "apt -y update"

if [ ! -f /etc/timezone ]; then
  echo "Etc/UTC" > /etc/timezone
fi

DO "apt install -y tzdata"
DO "dpkg-reconfigure -f noninteractive tzdata"
DO "apt -y install gnupg net-tools curl"

if [[ "$DISTRO_CODENAME" != "trixie" ]]; then
  DO "apt -y install software-properties-common"
fi

# The supported platforms are experimentally more than only Ubuntu as
# publicly communicated to users.
#
# Depending on the intention of the user to proceed anyhow installing on
# a not supported distro we using the experimental package if it exists
# or trixie as fallback.
if echo "$DISTRO_CODENAME" | grep -vqE "^(bionic|bookworm|bullseye|buster|focal|jammy|noble|trixie)$"; then
  # In case of unsupported platforms we fallback on trixie
  echo "No packages available for the current distribution; the install script will use the trixie repository."
  DISTRO="debian"
  DISTRO_CODENAME="trixie"
fi

if [ -f /tmp/globaleaks.deb ]; then
  dpkg -i /tmp/globaleaks.deb || apt --fix-broken install -y
else
  echo "Adding GlobaLeaks PGP key to trusted APT keys"
  curl -sS https://deb.globaleaks.org/globaleaks.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/globaleaks.gpg

  echo "Updating GlobaLeaks apt source.list in /etc/apt/sources.list.d/globaleaks.list ..."
  echo "deb [signed-by=/etc/apt/trusted.gpg.d/globaleaks.gpg] https://deb.globaleaks.org $DISTRO_CODENAME/" > /etc/apt/sources.list.d/globaleaks.list

  DO "apt update -y"

  if [[ $VERSION ]]; then
    DO "apt install -y --no-install-recommends python3-munkres globaleaks=$VERSION"
  else
    DO "apt install -y --no-install-recommends python3-munkres globaleaks"
  fi
fi

echo "GlobaLeaks installation completed successfully."

if ! HAS_SYSTEMD; then
  echo "Skipping service start check (systemd not available or running in Docker)"
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
    echo "GlobaLeaks startup completed."
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
