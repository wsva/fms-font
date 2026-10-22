#!/usr/bin/env python3
"""Repair the "e is covered by the next letter" overhang in the Entenmann faces.

Root cause, read straight out of the METAFONT sources (wela14_def.mf):

    def latin_e (expr sx)=
      draw ((0,0){right}..(ebreite+0.5ut+0.5ht/m, ...){up}..(ebreite*(1-ef)+0.5ut+0.5ht/m, 0));
      xpos := sx + ebreite*(1-ef) + 0.5ut + 0.5ht/m;
    enddef;
    ebreite := 8ut;  ef := 0.3;

The bowl is drawn out to `ebreite + ...` but the exit point - and therefore the
charwd the tfm publishes - stops `ebreite*ef` = 8 * 0.3 = 2.4ut short. At the
16.635 font units per ut# of these conversions that is ~40 units, which is why
the measured ink overrun of 'e' is 50 where every other lowercase letter's is
10-11 (the pen radius). The next letter therefore starts ~40 units inside the
bowl and paints over it. The same macro shape is reused by wesa (+77 units of
excess) and wedn (+36); wesu and weva draw 'e' without the overrun and are
unaffected.

This is a property of the source, not of the conversion: TeX reads the same tfm
charwd and overlaps identically. But the author's own cure is visible in the
sources too - he cut context variants ("e nach r", "e nach b,o,v,w") with wider
charwds and wired them through TeX ligature tables. ligatures.py now carries
those tables into the face as GSUB, which is the real fix; widening the advance
stays behind it as the general case, so an "e" that reaches no ligature context
at all - standing alone, or in a face that was never decorated - still leaves
room for whatever comes next.

The repair is width-only: advance := ink right edge - the family's own median
lowercase overrun, so 'e' joins exactly like its neighbours (in a slanted face
that median is large by design, and the correction tracks it). Detection is
two-sided so the pass converges from any starting advance - a face that was
already corrected, or one that was corrected wrongly, lands on the same value -
and no outline moves, so nothing is redrawn. Lowercase a-z only: capitals like U
overrun by ~27 units, which is flourish rather than a collision the user
reported, and is left alone.
"""

import statistics

from fontTools.pens.boundsPen import BoundsPen

# How far a glyph's overrun may deviate from its neighbours' before it is
# corrected, in units of a 1000-unit em. 15 sits well above the widest intended
# join (Suetterlin v/w reach ~17 over a median of ~10) and far below the defect
# (36-77 over).
MAX_EXTRA = 15


def _lowercase_rows(font):
    """[(glyph name, advance, ink xMax)] for a-z, the letters this repair targets."""
    cmap = font.getBestCmap()
    glyf, hmtx, gs = font["glyf"], font["hmtx"], font.getGlyphSet()
    rows, seen = [], set()
    for ch in range(ord("a"), ord("z") + 1):
        name = cmap.get(ch)
        if not name or name in seen or glyf[name].numberOfContours == 0:
            continue
        seen.add(name)
        bp = BoundsPen(gs)
        gs[name].draw(bp)
        if bp.bounds is None:
            continue
        rows.append((name, hmtx[name][0], bp.bounds[2]))
    return rows


def repair_overhang(font, label=""):
    """Widen the lowercase glyphs whose ink overruns the advance abnormally.

    Returns [(glyph, old advance, new advance)]; empty when the face is clean.
    """
    upm = font["head"].unitsPerEm
    rows = _lowercase_rows(font)
    if len(rows) < 5:
        return []
    median = statistics.median(x_max - adv for _n, adv, x_max in rows)
    tol = MAX_EXTRA * upm / 1000.0
    hmtx = font["hmtx"]
    changed = []
    for name, adv, x_max in rows:
        if abs((x_max - adv) - median) > tol:
            new = round(x_max - median)
            if new != adv:
                hmtx.metrics[name] = (new, hmtx[name][1])
                changed.append((name, adv, new))
    if changed:
        # the average advance in OS/2 is a static sum, so keep it honest
        cmap = font.getBestCmap()
        widths = [hmtx.metrics[name][0] for code, name in cmap.items() if 33 <= code <= 126]
        if widths:
            font["OS/2"].xAvgCharWidth = round(sum(widths) / len(widths))
    if changed and label:
        for name, adv, new in changed:
            print(f"  {label}: {name} advance {adv} -> {new} ({new - adv:+d})")
    return changed
