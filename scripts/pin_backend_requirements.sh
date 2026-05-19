#!/bin/bash
set -euo pipefail

REQ_DIR="$(dirname "${BASH_SOURCE[0]}")/../backend/requirements"

for in_file in "${REQ_DIR}"/requirements.in.*; do
  version="${in_file##*.}"
  echo "Compiling requirements.in.${version} -> requirements.txt.${version}"
  pip-compile --strip-extras --no-header --generate-hashes --allow-unsafe \
    --output-file="${REQ_DIR}/requirements.txt.${version}" \
    "${in_file}"
done
