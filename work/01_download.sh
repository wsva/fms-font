#!/bin/bash
# Download the schulschriften package from CTAN and extract the wela sources.
set -euo pipefail
WORK=/tmp/wela-work
mkdir -p "$WORK"
cd "$WORK"
if [ ! -s schulschriften.zip ] || ! unzip -tq schulschriften.zip >/dev/null 2>&1; then
  rm -f schulschriften.zip
  curl -L --fail --retry 3 -o schulschriften.zip https://mirror.ctan.org/fonts/schulschriften.zip
fi
unzip -o -q schulschriften.zip
echo "--- top level:"
ls schulschriften
echo "--- source/wela:"
ls schulschriften/source/wela 2>/dev/null || find schulschriften -name '*.mf' | head -30
echo "--- tex/wela:"
ls schulschriften/tex/wela 2>/dev/null || true
echo "--- any prebuilt font files (pfb/pfa/tfm/type3)?"
find schulschriften \( -name '*.pfb' -o -name '*.pfa' -o -name '*.tfm' -o -name '*.type3' \) | head -20 || true
