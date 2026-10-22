#!/usr/bin/env python3
"""Raw tfm block around a character, and what the sources say about it."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligatures import MF, SRC

text = open("/tmp/tfm.txt", encoding="latin-1").read().splitlines()
for i, line in enumerate(text):
    if line.strip().startswith("(CHARACTER C e"):
        print("\n".join(text[i:i + 7]))
print("total CHARACTER blocks:", sum(1 for l in text if "(CHARACTER" in l))
family = MF[sys.argv[1]]
codes = {}
BEGIN = re.compile(r'beginchar\(\s*(oct"[0-7]+"|"(?:\\.|[^"\\])*")\s*,\s*([^,)]+)')
for fn in sorted(os.listdir(os.path.join(SRC, family))):
    if fn.endswith(("_gr.mf", "_kl.mf", "_sz.mf")):
        for line in open(os.path.join(SRC, family, fn), encoding="latin-1"):
            m = BEGIN.search(line)
            if m:
                c = int(m.group(1)[4:-1], 8) if m.group(1).startswith("oct") else ord(m.group(1)[1])
                codes[c] = m.group(2).strip()
print("source beginchar for 0o145:", codes.get(101), " 0o157:", codes.get(111),
      " 0o162:", codes.get(114), " 0o5:", codes.get(5))
