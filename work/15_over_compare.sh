#!/usr/bin/env bash
# Dump advance/ink metrics for a-z of every family into one file, so 'e' can be
# compared against its peers and against the other scripts.
#
# Takes the font dir as $1 because this repo's scripts are commonly run as
# `sed 's/\r$//' file | bash`, which leaves $0 useless for locating the repo.
set -u
cd "${1:?usage: 15_over_compare.sh <font_dir>}"
out=work/out_over_compare.txt
: > "$out"
for x in la su va dn sas; do
  f="faces/entenmann-${x}-regular.ttf"
  [ -f "$f" ] || continue
  {
    echo "##### $x"
    python3 work/13_metrics.py "$f" glyphs | grep -E '^(ch|[a-z] )'
  } >> "$out" 2>&1
done
echo "wrote $out ($(grep -c . "$out") lines)"
