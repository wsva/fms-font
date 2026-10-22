#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print what a glyph actually hands to a pen, and what the flattener makes of it.

Used to debug 22_inkrender.py: if the polygons it builds do not cover the same
box as BoundsPen says the glyph does, the raster is lying and no conclusion about
collisions can be drawn from it.

Usage: 23_debugglyph.py <ttf> <char>
"""
import importlib.util
import os
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

# the renderer's module name starts with a digit, so it has to be loaded by path
_spec = importlib.util.spec_from_file_location(
    "inkrender", os.path.join(os.path.dirname(__file__), "22_inkrender.py"))
_inkrender = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_inkrender)
contours = _inkrender.contours

ttf, ch = sys.argv[1], sys.argv[2]
f = TTFont(ttf)
name = f.getBestCmap().get(ord(ch))
gs = f.getGlyphSet()

pen = RecordingPen()
gs[name].draw(pen)
print(f"glyph {name}: {len(pen.value)} pen ops")
for op, args in pen.value[:8]:
    print("   ", op, args)
if len(pen.value) > 8:
    print(f"    ... {len(pen.value) - 8} more")

bp = BoundsPen(gs)
gs[name].draw(bp)
print("BoundsPen box:", bp.bounds)

polys = contours(gs[name])
print(f"flattened to {len(polys)} contours, points={[len(p) for p in polys]}")
if polys:
    xs = [x for p in polys for x, _y in p]
    ys = [y for p in polys for _x, y in p]
    print(f"polygon box: {min(xs):.1f} {min(ys):.1f} {max(xs):.1f} {max(ys):.1f}")
