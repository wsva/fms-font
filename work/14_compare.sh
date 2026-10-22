#!/usr/bin/env bash
# Compare the overlap profile across the five Entenmann families (regular faces)
# and, for one family, across its four styles.
set -u
cd "$(dirname "$0")/.."

echo "=== per-family regular faces: how often is each letter the one getting covered"
for x in la su va dn sas; do
  f="faces/entenmann-${x}-regular.ttf"
  [ -f "$f" ] || continue
  echo "----- $x"
  python3 work/13_metrics.py "$f" pairs 2>&1 | tail -9
done

echo
echo "=== LA: 'e' metrics in every style"
for s in regular bold italic bold-italic; do
  f="faces/entenmann-la-${s}.ttf"
  [ -f "$f" ] || continue
  echo "----- $s"
  python3 work/13_metrics.py "$f" glyphs 2>&1 | grep -E '^(ch|[eonrt] )'
done
