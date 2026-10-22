#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a phrase from a face as plain ink, so the result can be looked at.

22_inkrender.py paints every glyph in its own colour, which answers "who covers
whom" but not "what does the reader see". This one draws the whole string in a
single colour - the same thing a browser draws - and shades pixels covered by
more than one glyph darker, so a collision is visible as a blot rather than as
a statistic.

Give it the .fea 40_build_gsub.py wrote and it shapes through the ligature
program first, which is what the browser will do.

Usage: 28_phrase.py <ttf> <out.png> [size_px_per_em] ["text"] [--fea file.fea]
"""
import importlib.util
import os
import sys

from fontTools.ttLib import TTFont

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ink22", os.path.join(_here, "22_inkrender.py"))
ink22 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ink22)

_spec = importlib.util.spec_from_file_location("shape41", os.path.join(_here, "41_shape.py"))
shape41 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shape41)

PAD = ink22.PAD


def main():
    args = [a for a in sys.argv[1:] if a != "--fea"]
    fea = sys.argv[sys.argv.index("--fea") + 1] if "--fea" in sys.argv else None
    ttf, out, size = args[0], args[1], float(args[2]) if len(args) > 2 else 96
    text = args[3] if len(args) > 3 else "Fremdsprachen machen Spa"

    f = TTFont(ttf)
    upm = f["head"].unitsPerEm
    cmap, hmtx, gs = f.getBestCmap(), f["hmtx"], f.getGlyphSet()
    asc, desc = f["hhea"].ascent, f["hhea"].descent
    sx = sy = size / upm
    if fea:
        # a word only joins at its start when something stands before it, so the
        # probe is shaped inside a sentence the way a browser would see it, then
        # the two padding spaces come back off
        glyphs = shape41.shape(fea, f, " " + text + " ")[1:-1]
    else:
        glyphs = [(cmap[ord(c)], hmtx[cmap[ord(c)]][0]) for c in text if ord(c) in cmap]
    w = int(sum(a for _, a in glyphs) * sx + 2 * PAD * sx)
    h = int((asc - desc) * sy + 2 * PAD * sy)
    baseline_row = int(asc * sy + PAD * sy)

    cover = [[0] * w for _ in range(h)]
    pen_x = PAD
    missing = [c for c in text if ord(c) not in cmap]
    for name, adv in glyphs:
        polys = [[(x + pen_x, y) for x, y in c]
                 for c in ink22.contours(gs[name], gs)]
        ink22.fill(cover, polys, w, h, sx, sy, baseline_row)
        pen_x += adv

    pixels = [[(255, 255, 255)] * w for _ in range(h)]
    clashes = 0
    for y in range(h):
        for x in range(w):
            if cover[y][x] == 1:
                pixels[y][x] = (25, 25, 25)
            elif cover[y][x] > 1:
                pixels[y][x] = (230, 40, 40)
                clashes += 1
    ink22.png(out, pixels, w, h)
    print(f"{os.path.basename(ttf)}: '{text}' {w}x{h} at {size:.0f}px/em "
          f"glyphs={len(glyphs)} overlapped={clashes} missing={''.join(missing) or '-'} -> {out}")


if __name__ == "__main__":
    main()
