#!/bin/bash
# This script bumps the project version across multiple files
# The script is expected to be run from the project's root directory
# with new version as the first argument
set -e

if [[ "$1" != "" ]]; then
	echo "Updating version to v$1"

	ROOTDIR=$(pwd)

	sed -i "s/^__version__ =.*/__version__ = '$1'/g" "$ROOTDIR"/backend/globaleaks/__init__.py

	sed -i "s/\"version\":.*/\"version\": \"$1\",/g" "$ROOTDIR"/client/package.json

	awk -v ver="$1" 'BEGIN{cnt=0} /"version":/ && cnt<2 {sub(/"version": "[^"]*"/, "\"version\": \"" ver "\""); cnt++} 1' "$ROOTDIR/client/npm-shrinkwrap.json" > tmp && mv tmp "$ROOTDIR/client/npm-shrinkwrap.json"

	sed -i "s/^releaseDate:.*/releaseDate: '$(date +'%Y-%m-%d')'/g" "$ROOTDIR"/publiccode.yml

	sed -i "s/softwareVersion:.*/softwareVersion: $1/g" "$ROOTDIR"/publiccode.yml

	echo -e "globaleaks ($1) stable; urgency=medium

  * New stable release

 -- GlobaLeaks software signing key <info@globaleaks.org>  $(date --rfc-email)\n\n$(cat debian/changelog)" > "$ROOTDIR"/debian/changelog

        git commit -a -m "Bump to version $1"

        git tag -s v$1 -m 'GlobaLeaks version $1' --force
else
	echo -e "Please specify a version"
	exit 1
fi
