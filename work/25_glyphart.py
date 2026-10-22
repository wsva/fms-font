#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASCII-art one glyph through the real 22_inkrender pipeline.

Prints the flattened contours and then the raster, so a broken result can be
attributed to either the flattener or the filler instead of guessed at.

Usage: 25_glyphart.py <ttf> <char> [width]
"""
import importlib.util
import os
import sys

from fontTools.ttLib import TTFont

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("inkrender", os.path.join(here, "22_inkrender.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

ttf, ch = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 60

f = TTFont(ttf)
upm = f["head"].unitsPerEm
name = f.getBestCmap().get(ord(ch))
gs = f.getGlyphSet()
polys = m.contours(gs[name])
xs = [x for p in polys for x, _y in p]
ys = [y for p in polys for _x, y in p]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
print(f"{name}: {len(polys)} contours, box {x0:.0f} {y0:.0f} .. {x1:.0f} {y1:.0f}")

sx = cols / (x1 - x0 + 1)
sy = sx / 2                     # terminal cells are ~2:1, so squash the y axis
rows = int((y1 - y0 + 1) * sy) + 1
w, h = cols + 2, rows + 2
mask = [[0] * w for _ in range(h)]
shifted = [[(x - x0, y - y0) for x, y in p] for p in polys]
m.fill(mask, shifted, w, h, sx, sy, h - 1)
for row in mask:
    print("".join("#" if v else "." for v in row))
