#!/usr/bin/env bash
set -euo pipefail

URL="https://mirrors.ctan.org/fonts/fontawesome7.zip"
ZIP="fontawesome7.zip"
SRC="fontawesome7"
OUT="texmf"

echo "Downloading fontawesome7"
mkdir -p _static/fa7 && curl -L "https://use.fontawesome.com/releases/v7.2.0/fontawesome-free-7.2.0-web.zip" -o /tmp/fa7.zip && unzip -q /tmp/fa7.zip -d _static/fa7 && mv _static/fa7/fontawesome-free-7.2.0-web/* _static/fa7/ && rmdir _static/fa7/fontawesome-free-7.2.0-web

echo "Downloading fontawesome7 package from CTAN…"
curl -L "$URL" -o "$ZIP"

echo "Extracting…"
unzip -q "$ZIP"
rm "$ZIP"

mkdir -p \
  "$OUT/fonts/enc/dvips/fontawesome7" \
  "$OUT/fonts/map/dvips/fontawesome7" \
  "$OUT/fonts/opentype/public/fontawesome7" \
  "$OUT/fonts/tfm/public/fontawesome7" \
  "$OUT/fonts/type1/public/fontawesome7" \
  "$OUT/tex/latex/fontawesome7"

mv "$SRC/map"/* "$OUT/fonts/map/dvips/fontawesome7/"
mv "$SRC/enc/"* "$OUT/fonts/enc/dvips/fontawesome7/"
mv "$SRC/opentype/"* "$OUT/fonts/opentype/public/fontawesome7/"
mv "$SRC/tfm/"* "$OUT/fonts/tfm/public/fontawesome7/"
mv "$SRC/type1/"* "$OUT/fonts/type1/public/fontawesome7/"
mv "$SRC/tex/"* "$OUT/tex/latex/fontawesome7/"

rm -rf "$SRC"
