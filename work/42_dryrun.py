#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dry-run the ligature program over every family, so a rollout knows what works.

Decorates each face in memory and throws it away, reporting the rule counts or
the error - a family whose program does not settle has to be found here rather
than half way through writing binaries.

Usage: 42_dryrun.py [style]
"""
import os
import re
import sys
import traceback

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
from ligatures import MF, Face, decorate  # noqa: E402

FACES = os.path.join(_here, "..", "faces")
style = sys.argv[1] if len(sys.argv) > 1 else "regular"

for short, family in sorted(MF.items()):
    path = os.path.join(FACES, f"entenmann-{short}-{style}.ttf")
    try:
        face = Face(path, family)
        decorate(face, verbose=False, label=short)
        made = [g for g in face.ttf.getGlyphOrder() if re.fullmatch(r"p[0-7]{3}(_[0-7]{3})*", g)]
        print(f"  {short:4} {family}: ok, {len(made)} composites, "
              f"{len(face.ttf.getGlyphOrder())} glyphs")
    except Exception:                                   # noqa: BLE001 - report all
        print(f"  {short:4} {family}: FAILED")
        traceback.print_exc(limit=3)
