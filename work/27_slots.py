#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every glyph in a face, with its advance and the code point that reaches it.

The METAFONT sources cut a second, wider form of most letters for word-final
position and let the tfm's ligature program choose between them; those slots
survive the conversion under whatever name tex256.enc gives them, so they have
to be found by looking at the whole inventory rather than by Unicode.

Usage: 27_slots.py <ttf>
"""
import sys

from fontTools.ttLib import TTFont

f = TTFont(sys.argv[1])
cmap = f.getBestCmap()
back = {}
for code, name in sorted(cmap.items()):
    back.setdefault(name, code)
hmtx = f["hmtx"]

for name in f.getGlyphOrder():
    code = back.get(name)
    print(f"{name:<16} adv={hmtx[name][0]:>5}  {'U+%04X' % code if code is not None else '-':>8}")
