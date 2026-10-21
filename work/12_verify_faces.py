#!/usr/bin/env python3
"""Sanity-check that weight and slant actually differ between faces, reading
the TTFs' glyph outlines for the letter 'a' (total ink bounding-box area and
contour count) as a proxy for stroke thickness / slant."""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

faces = {
    "regular": "/mnt/c/Users/yanan/code/fms-app/font/faces/entenmann-la-regular.ttf",
    "bold":    "/mnt/c/Users/yanan/code/fms-app/font/faces/entenmann-la-bold.ttf",
    "italic":  "/mnt/c/Users/yanan/code/fms-app/font/faces/entenmann-la-italic.ttf",
}

def stats(path):
    f = TTFont(path)
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()
    gid = cmap.get(ord("a"))
    if gid is None:
        return None
    pen = RecordingPen()
    gs[gid].draw(pen)
    pts = [p for op, args in pen.value for p in args if isinstance(p, tuple)]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    n_contours = sum(1 for op, _ in pen.value if op == "moveTo")
    # rough slant: correlate x-shift between low and high points
    return dict(points=len(pts), contours=n_contours,
                w=(max(xs) - min(xs)), h=(max(ys) - min(ys)))

for name, p in faces.items():
    print(f"{name:8} 'a' outline stats: {stats(p)}")
