#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Did the rebuilt faces actually reach the app, and do they carry the program?

public/fonts/ is what the webview loads, and it is a copy - a rebuild that was
never copied leaves the app serving the old binaries with every local check still
green. So compare the bytes, then read the tables off the shipped file: the space
(the tfm's boundarychar), the zero-width trigger that stands in for it at a block
edge, and the two lookups the program became.

Usage: 78_shipped_faces.py
"""
import glob
import hashlib
import os
import sys

from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
BUILT = os.path.join(HERE, "..", "faces")
SHIPPED = os.path.join(HERE, "..", "..", "public", "fonts")

bad = 0
for src in sorted(glob.glob(os.path.join(BUILT, "entenmann-*.woff2"))):
    name = os.path.basename(src)
    dst = os.path.join(SHIPPED, name)
    digest = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()  # noqa: E731
    if not os.path.exists(dst):
        print(f"MISSING   {name} - never copied into public/fonts")
        bad += 1
        continue
    if digest(src) != digest(dst):
        print(f"STALE     {name} - public/fonts holds a different build")
        bad += 1
        continue
    f = TTFont(dst)
    cmap = f.getBestCmap()
    names = set(f.getGlyphOrder())
    gsub = f["GSUB"].table if f.get("GSUB") else None
    tags = {fr.FeatureTag for fr in gsub.FeatureList.FeatureRecord} if gsub else set()
    problems = []
    if "space" not in names or cmap.get(0x20) != "space":
        problems.append("no space at U+0020")
    if "boundary" not in names or cmap.get(0x200B) != "boundary":
        problems.append("no boundary trigger at U+200B")
    if not {"calt", "liga"} <= tags:
        problems.append(f"GSUB features {sorted(tags)}")
    if not f.get("GPOS"):
        problems.append("no GPOS/kern")
    print(("OK       " if not problems else "BROKEN   ") + name +
          ("" if not problems else " - " + ", ".join(problems)))
    bad += bool(problems)

print("all 20 shipped faces carry the program" if not bad
      else f"{bad} faces need attention")
sys.exit(1 if bad else 0)
