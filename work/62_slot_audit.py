#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which codes of the ligature program does the converted face not have?

analyse() silently filters its alphabet to the slots the face actually carries, so
a slot that exists under a different glyph name in the TTF (fontforge renames some
on export) drops every rule that touches it - and a dropped rule is a missing join
in the middle of a word.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligatures import MF, SPACE, Face, enc_names

HERE = os.path.dirname(os.path.abspath(__file__))
FACES = os.path.join(HERE, "..", "faces")
SRC = os.path.join(HERE, "..", "metafont-source")

for short in ("su", "dn", "la", "sas", "va"):
    face = Face(os.path.join(FACES, f"entenmann-{short}-regular.ttf"), MF[short])
    order = set(face.ttf.getGlyphOrder())
    used = set()
    for r in face.rules:
        used |= {c for c in r.first if c != SPACE}
        used.add(r.second)
        if isinstance(r.result, int):
            used.add(r.result)
    for c in face.codes:
        used.add(c)
    names = enc_names()
    absent = sorted(c for c in used
                    if c in names and names[c] not in order and c != SPACE)
    print(f"--- {short}: {len(absent)} program codes with no glyph under the tex256 name")
    for c in absent:
        cmap = face.ttf.getBestCmap()
        # which glyph does the face actually put at that slot's unicode?
        alt = [g for g in order if g.lower() in names[c].lower()]
        print(f"    {oct(c)} {names[c]:16} rules touching it: "
              f"{sum(1 for r in face.rules if c in r.first or r.second == c or r.result == c)}"
              f"  similar names in font: {alt}")
    # and the reverse: codes the face has but the program never reaches
    print(f"    beginchar codes missing from the face: {len(face.missing)} {face.missing[:8]}")
