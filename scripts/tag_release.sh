#!/bin/bash
# This script tag a new release version
set -e

if [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	echo "Tagging version v$1"

        git tag -s "v$1" -m "GlobaLeaks version $1" --force
else
	echo -e "Please specify a valid version (expected format: X.Y.Z)"
	exit 1
fi
