#!/usr/bin/env bash
set -euo pipefail

mkdir -p _static/fonts
curl -L -o _static/fonts/inter-all-400-normal.woff https://cdn.jsdelivr.net/npm/@fontsource/inter@5.2.8/files/inter-all-400-normal.woff
curl -L -o _static/fonts/inter-all-700-normal.woff https://cdn.jsdelivr.net/npm/@fontsource/inter@5.2.8/files/inter-all-700-normal.woff
