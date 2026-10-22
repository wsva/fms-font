#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Why does a whole word cost more through the font than through TeX's program?

Print both settled sequences side by side, glyph name + advance per position.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligatures import MF, Face, decorate, resolve

shape = importlib.import_module("41_shape")
FACES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "faces")

short = sys.argv[1]
word = sys.argv[2]

face = Face(os.path.join(FACES, f"entenmann-{short}-regular.ttf"), MF[short])
decorate(face, verbose=False, label=short)
order = face.ttf.getGlyphOrder()
print("glyph names matching SS/germ/scharf:",
      [g for g in order if "SS" in g or "erm" in g or "charf" in g.lower()])
print("codes whose name is absent from the font:",
      [(f"{c:03o}", face.name_of[c]) for c in face.codes if face.name_of[c] not in set(order)])

index = {}
for r in face.rules:
    if r.action == "kern" or r.word_start:
        continue
    for head in r.first:
        index.setdefault((head, r.second), []).append(r)

cmap = face.ttf.getBestCmap()
codes = [ord(c) for c in word if ord(c) in cmap]
print("input codes:", " ".join(f"{c:03o}" for c in codes))
try:
    settled = resolve(codes, index)
except RuntimeError as e:
    settled = None
    print("TeX does not settle:", e)
if settled:
    print("TeX :", " ".join(f"{face.name_of[c]}({face.adv(c)})" for c in settled),
          "=", sum(face.adv(c) for c in settled))
got = shape.shape(face.fea, face.ttf, word)
print("font:", " ".join(f"{n}({a})" for n, a in got), "=", sum(a for _, a in got))
