#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Walk the token stream of one ligtable through the parser, one step at a time.

Usage: 58_steptok.py <family> <line-with-ligtable>   (line number of the table's
first line; the dump stops at the next `ligtable` or end of file)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligparse import TOKEN

HERE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(HERE, "..", "metafont-source", sys.argv[1], f"{sys.argv[1]}14_lig.mf")
start = int(sys.argv[2])
text = "\n".join(open(path, encoding="latin-1").read().splitlines()[start - 1:])
m = re.search(r"ligtable", text)
text = re.sub(r"%[^\n]*", "", text[m.start():])
nxt = text.find("ligtable", 8)          # dump one table, not the rest of the file
if nxt > 0:
    text = text[:nxt]
toks = [(m2.lastgroup, m2.group()) for m2 in TOKEN.finditer(text)]
for i, (k, v) in enumerate(toks):
    print(f"{i:3} {k:6} {v}")
