#!/bin/bash

set -e

TARGETS="bionic bookworm bullseye buster focal jammy noble"
DISTRIBUTION="bookworm"
TAG="main"
LOCAL_ENV=0
NOSIGN=0
PUSH=0

usage() {
  echo "GlobaLeaks Build Script"
  echo "Valid options:"
  echo " -h"
  echo -e " -t tagname (build specific release/branch)"
  echo -e " -l (Use local repository & enviroment)"
  echo -e " -d distribution (available: bionic, bookworm, bullseye, buster, focal, jammy, noble)"
  echo -e " -n (do not sign)"
  echo -e " -p (push on repository)"
}

while getopts "d:t:nph:l" opt; do
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

if ! [[ $TARGETS =~ $DISTRIBUTION ]] && [[ $DISTRIBUTION != 'all' ]]; then
 usage
 exit 1
fi

if [ "$DISTRIBUTION" != 'all' ]; then
  TARGETS=$DISTRIBUTION
fi

# Preliminary Requirements Check
ERR=0
echo "Checking preliminary GlobaLeaks Build requirements"
for REQ in git npm debuild dput
do
  if which $REQ >/dev/null; then
    echo " + $REQ requirement meet"
  else
    ERR=$((ERR+1))
    echo " - $REQ requirement not meet"
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

if [ $LOCAL_ENV -eq 1 ]; then
  git clone --branch="$TAG" --depth=1 file://$(pwd)/../../../whistleblowing-software .
else
  git clone --branch="$TAG" --depth=1 https://github.com/globaleaks/whistleblowing-software.git .
fi

cd client && npm install -d && ./node_modules/grunt/bin/grunt build

cd $ROOTDIR

for TARGET in $TARGETS; do
  echo "Packaging GlobaLeaks for:" $TARGET

  BUILDDIR="build/$TARGET"

  [ -d $BUILDDIR ] && rm -rf $BUILDDIR

  mkdir -p $BUILDDIR
  cp -r $BUILDSRC $BUILDDIR
  cd "$BUILDDIR/src"

  rm debian/control backend/requirements.txt

  if [ "$TARGET" == "bionic" ]; then
    echo 10 > debian/compat
  else
    echo 12 > debian/compat
  fi

  cp debian/controlX/control.$TARGET  debian/control
  cp backend/requirements/requirements-$TARGET.txt backend/requirements.txt

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

    BUILDDIR="GLRelease-$TARGET"

    cp -r $BUILDSRC $BUILDDIR

    dput globaleaks globaleaks*changes

    cd ../../
  done
fi
