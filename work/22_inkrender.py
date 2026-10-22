#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rasterise a string from a face file and paint real ink collisions in red.

The metrics scripts can only report where two glyphs' bounding boxes overlap,
which in a joined cursive is normal and tells nothing. This walks the outlines,
fills them scanline by scanline, and marks any pixel covered by more than one
glyph - so a letter that gets painted over shows up as red where the damage is,
and a healthy join shows up as a single black hairline.

Usage: 22_inkrender.py <ttf> <out.png> [size_px_per_em] ["text"]
"""
import math
import struct
import sys
import zlib

from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.ttLib import TTFont

MAX_SEG = 6          # px per straight segment when flattening a curve
PAD = 200            # font units of slack around the string, for overhanging ink


def _bez(points, steps):
    """Sample a bezier run (no duplicate of the start point) via De Casteljau."""
    for i in range(1, steps + 1):
        t = i / steps
        pts = list(points)
        while len(pts) > 1:
            pts = [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
                   for (x0, y0), (x1, y1) in zip(pts, pts[1:])]
        yield pts[0]


def _reach(points):
    return sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(points, points[1:]))


def _steps(points):
    return max(2, min(64, int(_reach(points) / MAX_SEG)))


def _arcs(start, args, closes_on_offcurve):
    """Split a TrueType off-curve run into individual quadratics.

    Consecutive off-curve points share an implied on-curve at their midpoint -
    feeding the whole run to one high-order bezier instead would distort every
    round letter, which is exactly what is being inspected here.
    """
    offs = list(args)
    end = start if closes_on_offcurve else offs.pop()
    arcs, prev = [], start
    for i, control in enumerate(offs):
        if i == len(offs) - 1:
            nxt = end
        else:
            other = offs[i + 1]
            nxt = ((control[0] + other[0]) / 2, (control[1] + other[1]) / 2)
        arcs.append((prev, control, nxt))
        prev = nxt
    return arcs


def contours(glyph, glyphSet=None):
    """Flatten one glyph into polygons of (x, y) font units.

    Pass the glyphSet for a face with composites: a plain RecordingPen just notes
    the addComponent call and never sees the parts.
    """
    pen = DecomposingRecordingPen(glyphSet) if glyphSet else RecordingPen()
    glyph.draw(pen)
    out, cur = [], []
    for op, args in pen.value:
        if op == "moveTo":
            cur = [args[0]]
        elif op == "lineTo":
            cur.append(args[0])
        elif op == "qCurveTo":
            if not cur:
                continue
            for a, b, c in _arcs(cur[-1], args, args[-1] is None):
                cur.extend(_bez([a, b, c], _steps([a, b, c])))
        elif op == "curveTo":
            if cur:
                cur.extend(_bez([cur[-1], *args], _steps([cur[-1], *args])))
        elif op in ("closePath", "endPath"):
            if len(cur) > 2:
                out.append(cur)
            cur = []
    return [c for c in out if len(c) > 2]


def fill(mask, polys, w, h, sx, sy, baseline_row):
    """Even-odd scanline fill; adds one to mask[y][x] per glyph covering that pixel.

    Font units have y upwards and the image has y downwards, so a point at y
    font units above the baseline lands on image row baseline_row - y*sy.

    Rows and columns are sampled at pixel centres. mftrace outlines have a point
    roughly every 1.5 font units, so most edges are shorter than a pixel: an
    edge range computed with int() would be empty for them and the letter would
    dissolve into specks. ceil/floor around the half-pixel offset is what keeps
    a sub-pixel edge counted in the one row it touches.
    """
    rows = [[] for _ in range(h)]
    for poly in polys:
        pts = [(x * sx, baseline_row - y * sy) for x, y in poly]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if y0 == y1:
                continue
            lo, hi = sorted((y0, y1))
            for iy in range(max(0, math.ceil(lo - 0.5)), min(h - 1, math.floor(hi - 0.5)) + 1):
                rows[iy].append(x0 + (x1 - x0) * ((iy + 0.5 - y0) / (y1 - y0)))
    for y, xs in enumerate(rows):
        if not xs:
            continue
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            for x in range(max(0, math.ceil(a - 0.5)), min(w - 1, math.floor(b - 0.5)) + 1):
                mask[y][x] += 1


def png(path, pixels, w, h):
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in pixels)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        fh.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        fh.write(chunk(b"IEND", b""))


def main():
    ttf, out = sys.argv[1], sys.argv[2]
    size = float(sys.argv[3]) if len(sys.argv) > 3 else 96
    text = sys.argv[4] if len(sys.argv) > 4 else "Fremdsprachen machen Spa\u00df"

    f = TTFont(ttf)
    upm = f["head"].unitsPerEm
    cmap, hmtx, gs = f.getBestCmap(), f["hmtx"], f.getGlyphSet()
    asc, desc = f["hhea"].ascent, f["hhea"].descent
    sx = sy = size / upm
    w = int(sum(hmtx[cmap[ord(c)]][0] for c in text if ord(c) in cmap) * sx + 2 * PAD * sx)
    h = int((asc - desc) * sy + 2 * PAD * sy)
    baseline_row = int(asc * sy + PAD * sy)

    cover = [[0] * w for _ in range(h)]
    pen_x = PAD
    drawn = 0
    # Painted in document order, later glyphs overwriting earlier ones - exactly
    # what a browser does. Colouring each glyph differently therefore shows who
    # covers whom, which no amount of box arithmetic can.
    palette = [(20, 20, 20), (210, 40, 40), (40, 90, 210), (30, 150, 60),
               (180, 60, 180), (230, 140, 20), (0, 150, 160), (120, 70, 20)]
    painted = [[(255, 255, 255)] * w for _ in range(h)]
    for idx, ch in enumerate(text):
        name = cmap.get(ord(ch))
        if not name:
            continue
        polys = [[(x + pen_x, y) for x, y in c] for c in contours(gs[name], gs)]
        drawn += len(polys)
        fill(cover, polys, w, h, sx, sy, baseline_row)
        solo = [[0] * w for _ in range(h)]
        fill(solo, polys, w, h, sx, sy, baseline_row)
        colour = palette[idx % len(palette)]
        for y in range(h):
            for x in range(w):
                if solo[y][x]:
                    painted[y][x] = colour
        pen_x += hmtx[name][0]

    pixels = [[(255, 255, 255)] * w for _ in range(h)]
    clashes = ink = 0
    for y in range(h):
        for x in range(w):
            if cover[y][x] == 1:
                pixels[y][x] = painted[y][x]
                ink += 1
            elif cover[y][x] > 1:
                pixels[y][x] = (220, 30, 30)
                clashes += 1
    png(out, pixels, w, h)
    print(f"{ttf.split('/')[-1]}: {w}x{h} at {size:.0f}px/em, ink={ink} "
          f"overlapped={clashes} contours={drawn} -> {out}")


if __name__ == "__main__":
    main()
