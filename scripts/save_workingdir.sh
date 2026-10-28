#!/bin/bash
# Run after Cypress prints "Run Finished" and attachment delivery completes.
# Stop the backend before copying the working directory.
set -e

if [ "${1:-}" = '-h' ] || [ "${1:-}" = '--help' ]; then
  echo "Usage: $0 [WORKINGDIR] [DESTINATION]"
  exit 0
fi
if [ "$#" -gt 2 ]; then
  echo "Usage: $0 [WORKINGDIR] [DESTINATION]" >&2
  exit 1
fi

ROOTDIR=$(cd "$(dirname "$0")/.." && pwd)
SOURCE=$(realpath -e -- "${1:-$ROOTDIR/backend/workingdir}")
for entry in globaleaks.db files attachments; do
  if [ ! -e "$SOURCE/$entry" ] || [ -L "$SOURCE/$entry" ]; then
    echo "Expected an existing file or directory: $SOURCE/$entry" >&2
    exit 1
  fi
done

VERSION=$(python3 - "$SOURCE/globaleaks.db" <<'PY'
import json
import sqlite3
import sys
from urllib.parse import quote

with sqlite3.connect('file:' + quote(sys.argv[1]) + '?mode=ro', uri=True) as conn:
    version = json.loads(conn.execute("SELECT value FROM config WHERE tid = 1 AND var_name = 'version_db'").fetchone()[0])
if isinstance(version, bool) or not isinstance(version, int) or version < 1:
    sys.exit('Expected an integer database version')
print(version)
PY
)
DESTINATION=${2:-$ROOTDIR/backend/globaleaks/tests/data/workingdirs/populated/$VERSION}
if [ -L "$DESTINATION" ]; then
  echo "Destination must not be a symlink" >&2
  exit 1
fi
DESTINATION=$(realpath -m -- "$DESTINATION")
case "$DESTINATION/" in
  "$SOURCE/"*) echo "Destination must be outside the working directory" >&2; exit 1 ;;
esac
case "$SOURCE/" in
  "$DESTINATION/"*) echo "Destination must not contain the working directory" >&2; exit 1 ;;
esac

mkdir -p -- "$(dirname "$DESTINATION")"
STAGING=$(mktemp -d "$DESTINATION.XXXXXXXX")
trap 'rm -rf -- "$STAGING"' EXIT
cp -a -- "$SOURCE/globaleaks.db" "$SOURCE/files" "$SOURCE/attachments" "$STAGING/"
if [ ! -e "$STAGING/attachments/untracked-migration-fixture.txt" ] &&
   [ ! -L "$STAGING/attachments/untracked-migration-fixture.txt" ]; then
  printf 'untracked migration fixture\n' > "$STAGING/attachments/untracked-migration-fixture.txt"
fi
rm -rf -- "$DESTINATION"
mv -- "$STAGING" "$DESTINATION"
echo "Saved version $VERSION fixture to $DESTINATION"
