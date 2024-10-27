#!/bin/bash
# This script tag a new release version
set -e

if [[ "$1" != "" ]]; then
	echo "Tagging version v$1"

        git tag -s v$1 -m 'GlobaLeaks version $1' --force
else
	echo -e "Please specify a version"
	exit 1
fi
