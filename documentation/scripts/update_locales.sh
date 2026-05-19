#!/bin/bash
set -euo pipefail

LANGUAGES=("it" "en" "fr" "es" "de" "ru" "ar" "zh_CN")
POT_DIR="_build/gettext"

rm -rf "$POT_DIR"
sphinx-build -b gettext . "$POT_DIR"

for LANG in "${LANGUAGES[@]}"; do
  echo "Updating documentation translations for language: $LANG"
  sphinx-intl update -p "$POT_DIR" -l "$LANG"
done

sphinx-intl build
