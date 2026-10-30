#!/bin/bash
# Saves the working directory left by a run of the end-to-end suite as the
# populated working directory of its database version, the one the migration
# tests start from. Run it with the backend stopped: the copy is a plain one.
set -e

ROOTDIR=$(cd "$(dirname "$0")/.." && pwd)
SOURCE=${1:-$ROOTDIR/backend/workingdir}

VERSION=$(python3 -c "import sqlite3, sys; print(sqlite3.connect('file:' + sys.argv[1] + '?mode=ro', uri=True).execute(\"SELECT value FROM config WHERE tid = 1 AND var_name = 'version_db'\").fetchone()[0])" "$SOURCE/globaleaks.db")
DESTINATION=$ROOTDIR/backend/globaleaks/tests/data/workingdirs/populated/$VERSION

rm -rf "$DESTINATION.new"
mkdir -p "$DESTINATION.new"
cp -a "$SOURCE/globaleaks.db" "$DESTINATION.new/"
for entry in files attachments tenants; do
  if [ -d "$SOURCE/$entry" ]; then
    cp -a "$SOURCE/$entry" "$DESTINATION.new/"
  fi
done

rm -rf "$DESTINATION"
mv "$DESTINATION.new" "$DESTINATION"
echo "Saved the working directory of version $VERSION in $DESTINATION"
