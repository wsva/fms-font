#!/usr/bin/env python3
"""Read the advance of a list of characters straight out of the shipped WOFF2s.

This is the file the app actually loads, so it is the last place a metrics fix
can be confirmed before a browser is involved.

Usage: 20_shipped_check.py <woff2> [...]
"""
import sys
from fontTools.ttLib import TTFont

for path in sys.argv[1:]:
    f = TTFont(path)
    cmap, hmtx = f.getBestCmap(), f["hmtx"]
    upm = f["head"].unitsPerEm
    def adv(ch):
        name = cmap.get(ord(ch))
        return hmtx[name][0] if name else 0
    print(f"{path.split('/')[-1]:<34} upm={upm} "
          f"a={adv('a')} e={adv('e')} o={adv('o')} n={adv('n')} "
          f"| e/em={adv('e') / upm:.3f}")
