#!/usr/bin/env bash
# Before/after per-letter cut profile: `before` is the committed face, the other
# column the working tree one. Takes the font dir as $1.
set -u
cd "${1:?usage: 19_follow_compare.sh <font_dir>}"
before=/tmp/entenmann_before
rm -rf "$before"; mkdir -p "$before"
out=work/out_follow.txt
: > "$out"
for p in la-regular la-italic la-bold sas-regular dn-regular su-regular va-regular; do
  f="faces/entenmann-${p}.ttf"
  git show "HEAD:${f}" > "$before/entenmann-${p}.ttf" 2>/dev/null || continue
  {
    echo "##### $p   (before = committed, after = working tree)"
    python3 work/18_follow.py "$before/entenmann-${p}.ttf" "$f"
  } >> "$out" 2>&1
done
echo "wrote $out"
