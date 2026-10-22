#!/usr/bin/env bash
# Worst remaining ink overlaps between adjacent letters, post-repair.
# Takes the font dir as $1 (see 15_over_compare.sh for why).
set -u
cd "${1:?usage: 17_pairs.sh <font_dir>}"
out=work/out_pairs.txt
: > "$out"
# Upright faces only: in a slanted face every glyph's ink box shifts right with
# height, so a box-level "overlap" there is the design, not a collision.
for p in la-regular sas-regular dn-regular su-regular va-regular; do
  {
    echo "##### $p"
    python3 work/13_metrics.py "faces/entenmann-${p}.ttf" pairs | sed -n '1,10p'
  } >> "$out" 2>&1
done
echo "wrote $out"
