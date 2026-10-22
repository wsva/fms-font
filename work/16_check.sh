#!/usr/bin/env bash
# Dump advance/ink metrics for a-z of the LA styles into one file, so the
# post-repair profile can be checked letter by letter (the slanted faces shift
# ink rightwards, which the median baseline has to absorb).
#
# Takes the font dir as $1 because this repo's scripts are commonly run as
# `sed 's/\r$//' file | bash -s -- <dir>`, which leaves $0 useless.
set -u
cd "${1:?usage: 16_check.sh <font_dir>}"
out=work/out_check.txt
: > "$out"
for f in la su va dn sas; do
  for s in regular italic; do
    p="faces/entenmann-${f}-${s}.ttf"
    [ -f "$p" ] || continue
    {
      echo "##### ${f}-${s}"
      python3 work/13_metrics.py "$p" glyphs | grep -E '^(ch|[a-z] )'
    } >> "$out" 2>&1
  done
done
echo "wrote $out"
