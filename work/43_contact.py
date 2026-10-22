#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One line of German in each of the five scripts, stacked into a contact sheet.

The point is to look at the result rather than at metrics: a family whose joins
came out wrong should be seen here, not after it ships. Each row is shaped
through that family's own program (41_shape.py) and drawn as plain ink.

Usage: 43_contact.py [size_px_per_em] ["text"]
"""
import importlib.util
import os
import sys

from fontTools.ttLib import TTFont

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_here, file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ink22 = _load("ink22", "22_inkrender.py")
shape41 = _load("shape41", "41_shape.py")
lig = _load("ligatures", "ligatures.py")

PAD = ink22.PAD
FACES = os.path.join(_here, "..", "faces")
FEAS = os.path.join(_here, "features")


def row(ttf, base, text, size):
    """[(name, advance)] plus the drawn pixels for one line of text.

    The face on disk already carries the program and the composites it needs, so
    this reads the .fea that produced it rather than rebuilding one: the sheet
    then shows what actually shipped.
    """
    f = TTFont(ttf)
    with open(os.path.join(FEAS, base + ".fea"), encoding="utf-8") as fh:
        fea = fh.read()
    glyphs = shape41.shape(fea, f, " " + text + " ")[1:-1]
    upm = f["head"].unitsPerEm
    gs, asc, desc = f.getGlyphSet(), f["hhea"].ascent, f["hhea"].descent
    sx = sy = size / upm
    w = int(sum(a for _, a in glyphs) * sx + 2 * PAD * sx)
    h = int((asc - desc) * sy + 2 * PAD * sy)
    cover = [[0] * w for _ in range(h)]
    pen_x = PAD
    for name, adv in glyphs:
        polys = [[(x + pen_x, y) for x, y in c] for c in ink22.contours(gs[name], gs)]
        ink22.fill(cover, polys, w, h, sx, sy, int(asc * sy + PAD * sy))
        pen_x += adv
    return w, h, cover


def main():
    size = float(sys.argv[1]) if len(sys.argv) > 1 else 64
    text = sys.argv[2] if len(sys.argv) > 2 else "Und woher kommen Sie? Aus Afrika?"
    rows = []
    for short, family in sorted(lig.MF.items()):
        base = f"entenmann-{short}-regular"
        w, h, cover = row(os.path.join(FACES, base + ".ttf"), base, text, size)
        rows.append((short, w, h, cover))
        print(f"  {short}: {w}x{h}")

    gap = 12
    W = max(r[1] for r in rows)
    H = sum(r[2] for r in rows) + gap * (len(rows) - 1)
    pixels = [[(245, 245, 245)] * W for _ in range(H)]
    y0 = 0
    for short, w, h, cover in rows:
        for y in range(h):
            for x in range(w):
                pixels[y0 + y][x] = (25, 25, 25) if cover[y][x] else (255, 255, 255)
        y0 += h + gap
    out = os.path.join(_here, "contact.png")
    ink22.png(out, pixels, W, H)
    print(f"-> {out} {W}x{H}")


if __name__ == "__main__":
    main()
