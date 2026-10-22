#!/usr/bin/env python3
"""Worst ink cut each lowercase letter suffers from whatever follows it, for one
or more faces side by side.

Unlike the global pair ranking (13_metrics.py), this isolates the per-letter
profile: a letter whose advance is too short shows up as a deep cut while its
neighbours stay in a narrow band. With two fonts the columns come out
before/after, so a metrics change can be judged instead of assumed.

Usage: 18_follow.py <ttf> [<ttf> ...]
"""
import sys
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont


def profile(path):
    f = TTFont(path)
    hmtx, cmap, gs = f["hmtx"], f.getBestCmap(), f.getGlyphSet()
    box = {}
    for ch in range(ord("a"), ord("z") + 1):
        name = cmap.get(ch)
        if not name or f["glyf"][name].numberOfContours == 0:
            continue
        bp = BoundsPen(gs)
        gs[name].draw(bp)
        if bp.bounds:
            box[chr(ch)] = (hmtx[name][0], bp.bounds[0], bp.bounds[2])
    out = {}
    for a in box:
        adv_a, _x0a, x1a = box[a]
        worst, who = 0, ""
        for b in box:
            gap = adv_a + box[b][1] - x1a      # b's ink start vs a's ink end
            if gap < worst:
                worst, who = gap, b
        out[a] = (worst, who)
    return out


paths = sys.argv[1:]
profiles = [(p.split("/")[-1], profile(p)) for p in paths]
letters = sorted(set().union(*[set(p[1]) for p in profiles]))
head = f"{'ch':<4}" + "".join(f"{name[:18]:>20}" for name, _ in profiles)
print(head)
for ch in letters:
    row = f"{ch:<4}"
    for name, prof in profiles:
        worst, who = prof.get(ch, (0, "-"))
        row += f"{f'{worst:.0f} by {who}':>20}"
    print(row)
