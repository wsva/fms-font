#!/usr/bin/env python3
"""Report advance-width vs ink-bounds metrics for a converted Entenmann face and
rank the glyph pairs where the following glyph's ink starts before the previous
glyph's ink ends (i.e. a real overlap, not the intended cursive join).

Usage: 13_metrics.py <ttf> [pairs|glyphs]
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

path = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "pairs"

f = TTFont(path)
glyf = f["glyf"]
hmtx = f["hmtx"]
gs = f.getGlyphSet()
cmap = f.getBestCmap()

# ch -> (advance, xMin, xMax, right overflow past the advance, ink width)
info = {}
for ch, name in sorted(cmap.items()):
    if not name or name == ".notdef" or not (32 <= ch < 127 or ch > 0xC0):
        continue
    if glyf[name].numberOfContours == 0:
        continue
    adv, _lsb = hmtx[name]
    # Draw through a bounds pen: gives the real ink box, composites included,
    # rather than the on-curve control-point box.
    bp = BoundsPen(gs)
    gs[name].draw(bp)
    if bp.bounds is None:
        continue
    x_min, _y_min, x_max, _y_max = bp.bounds
    info[chr(ch)] = (adv, x_min, x_max, x_max - adv, x_max - x_min)

if mode == "glyphs":
    print(f"{'ch':<4}{'adv':>6}{'xMin':>7}{'xMax':>7}{'over':>7}{'ink':>7}")
    for ch, (adv, x0, x1, over, ink) in sorted(info.items()):
        print(f"{ch:<4}{adv:>6}{x0:>7}{x1:>7}{over:>7}{ink:>7}")
    sys.exit(0)

# Pairwise: pen advances by adv(a), then b's ink starts at xMin(b) relative to
# that origin. Overlap when a's ink extends past where b's ink begins.
bad = []
for a in info:
    adv_a, _x0a, x1a, _oa, _ia = info[a]
    for b in info:
        _adv_b, x0b, _x1b, _ob, _ib = info[b]
        gap = adv_a + x0b - x1a
        if gap < 0:
            bad.append((gap, a, b, adv_a, x1a, x0b))

bad.sort()
print(f"{len(bad)} overlapping pairs in {path.split('/')[-1]}, worst 25 "
      f"(gap = how far the next glyph's ink cuts into the previous one):")
for gap, a, b, adv_a, x1a, x0b in bad[:25]:
    print(f"  {a}{b}  gap={gap:>5}  adv({a})={adv_a:>4} inkEnd({a})={x1a:>4} inkStart({b})={x0b:>5}")

# Per-letter summary: how often is each letter the *victim*? In the pair a,b the
# pen has already advanced past a when b is drawn, so b paints on top of a: a is
# the letter being covered.
from collections import Counter
victim = Counter()
depth = Counter()
for gap, a, b, *_ in bad:
    victim[a] += 1
    depth[a] = min(depth[a], gap)
print("\nmost-covered letters (victim = letter whose ink the NEXT letter overlaps):")
for a, n in victim.most_common(12):
    adv_a, x0a, x1a, over_a, ink_a = info[a]
    print(f"  '{a}': covered by {n:>3} different letters, worst cut {depth[a]:>5} units "
          f"(adv={adv_a} inkWidth={ink_a} overflowPastAdvance={over_a})")
