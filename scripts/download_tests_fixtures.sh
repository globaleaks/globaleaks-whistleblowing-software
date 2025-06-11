#!/bin/bash

echo "Downloading test fixtures in client/crypress/fixtures/files"

# Directory to store files
TARGET_DIR="client/cypress/fixtures/files"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR" || exit 1

# List of files and URLs
declare -A files=(
  ["eicar.com"]="https://secure.eicar.org/eicar.com"
  ["eicar.com.txt"]="https://secure.eicar.org/eicar.com.txt"
  ["eicar_com.zip"]="https://secure.eicar.org/eicar_com.zip"
  ["eicarcom2.zip"]="https://secure.eicar.org/eicarcom2.zip"
)

# Download files if not already present
for filename in "${!files[@]}"; do
  if [ -f "$filename" ]; then
    echo "$filename already exists, skipping..."
  else
    echo "Downloading $filename..."
    curl -O "${files[$filename]}"
  fi
done
