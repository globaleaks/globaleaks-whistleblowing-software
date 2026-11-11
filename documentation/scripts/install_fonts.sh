#!/usr/bin/env bash
set -euo pipefail

mkdir -p _static/fonts
for subset in latin latin-ext; do
  for weight in 400 700; do
    curl -L -o _static/fonts/noto-sans-$subset-$weight-normal.woff https://cdn.jsdelivr.net/npm/@fontsource/noto-sans@5.3.0/files/noto-sans-$subset-$weight-normal.woff
  done
done
