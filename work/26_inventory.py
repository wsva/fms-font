#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""What is actually in a converted face: glyph inventory, slots, and the
positional variants the METAFONT source defines but the tfm ligatures select.

Usage: 26_inventory.py <ttf>
"""
import sys

from fontTools.ttLib import TTFont

f = TTFont(sys.argv[1])
order = f.getGlyphOrder()
cmap = f.getBestCmap()
hmtx = f["hmtx"]
print(f"{sys.argv[1].split('/')[-1]}: {len(order)} glyphs, {len(cmap)} cmap entries")

inv = {n: c for c, n in cmap.items()}
named = [g for g in order if not g.startswith("glyph")]
print(f"non-slot names ({len(named)}): {named[:40]}")

# The source puts the word-final / context forms above the ASCII range
# (oct 241..). Show every glyph whose name looks like a letter variant.
variants = {}
for g in order:
    base = g.split(".")[0].split("_")[0]
    if len(base) == 1 and base.isalpha():
        variants.setdefault(base, []).append(g)
for base in sorted(variants):
    if len(variants[base]) > 1:
        print(f"  {base}: " + ", ".join(
            f"{g}(adv={hmtx[g][0]},uni={hex(inv[g]) if g in inv else '-'})"
            for g in variants[base]))

zero = [g for g in order if hmtx[g][0] == 0 and g in inv and inv[g] > 32]
print(f"printable glyphs with zero advance ({len(zero)}): "
      + ", ".join(f"{g}@{hex(inv[g])}" for g in zero[:20]))
