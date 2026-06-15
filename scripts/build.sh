#!/bin/bash

set -e

TARGETS="bookworm bullseye focal jammy noble resolute trixie"
DISTRIBUTION="trixie"
TAG="stable"
LOCAL_ENV=0
NOSIGN=0
PUSH=0

usage() {
  echo "GlobaLeaks Build Script"
  echo "Valid options:"
  echo " -h"
  echo -e " -t tagname (build specific release/branch)"
  echo -e " -l (Use local repository & environment)"
  echo -e " -d distribution (available: bookworm, bullseye, focal, jammy, noble, resolute, trixie)"
  echo -e " -n (do not sign)"
  echo -e " -p (push on repository)"
}

while getopts "d:t:nph:lz" opt; do
  case $opt in
    d) DISTRIBUTION="$OPTARG"
    ;;
    t) TAG="$OPTARG"
    ;;
    n) NOSIGN=1
    ;;
    p) PUSH=1
    ;;
    l) LOCAL_ENV=1
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

case "$DISTRIBUTION" in
  bookworm|bullseye|focal|jammy|noble|resolute|trixie|all) ;;
  *) usage; exit 1 ;;
esac

if [ "$DISTRIBUTION" != 'all' ]; then
  TARGETS=$DISTRIBUTION
fi

# Preliminary Requirements Check
ERR=0
echo "Checking preliminary GlobaLeaks Build requirements"
for REQ in git npm debuild brotli
do
  if which $REQ >/dev/null; then
    echo " + $REQ requirement met"
  else
    ERR=$((ERR+1))
    echo " - $REQ requirement not met"
  fi
done

if [ $ERR -ne 0 ]; then
  exit 1
fi

ROOTDIR=$(pwd)

BUILDDIR="build"
BUILDSRC="$BUILDDIR/src"

[ -d $BUILDDIR ] && rm -rf $BUILDDIR

mkdir -p $BUILDSRC && cd $BUILDSRC

# Clone shallowly
if [ $LOCAL_ENV -eq 1 ]; then
  git clone --depth=1 file://$(pwd)/../../../globaleaks-whistleblowing-software .
else
  git clone --depth=1 https://github.com/globaleaks/globaleaks-whistleblowing-software.git .
fi

# Fetch and checkout the ref (branch or tag)
git fetch --depth=1 origin "$TAG"
git checkout FETCH_HEAD

cd client && npm ci -d && ./node_modules/grunt/bin/grunt build

cd $ROOTDIR

for TARGET in $TARGETS; do
  echo "Packaging GlobaLeaks for:" $TARGET

  BUILDDIR="build/$TARGET"

  [ -d $BUILDDIR ] && rm -rf $BUILDDIR

  mkdir -p $BUILDDIR
  cp -r $BUILDSRC $BUILDDIR
  cd "$BUILDDIR/src"

  rm debian/control backend/requirements.txt

  cp debian/controlX/control.$TARGET  debian/control
  cp backend/requirements/requirements.txt.$TARGET backend/requirements.txt

  sed -i "s/stable; urgency=/$TARGET; urgency=/g" debian/changelog

  if [ $NOSIGN -eq 1 ]; then
    debuild -i -us -uc -b
  else
    debuild -b
  fi

  cd ../../../
done

if [ $PUSH -eq 1 ]; then
  for TARGET in $TARGETS; do
    dput globaleaks "build/$TARGET/"globaleaks_*_amd64.changes
  done
fi
