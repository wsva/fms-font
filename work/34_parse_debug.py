#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Show every beginchar line and whether the parser sees it - the slot map in
33_map.py came out short of the oct 200.. range, so the regex is missing those
lines and this prints them verbatim (repr, to expose tabs and odd spacing).
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
mod = importlib.util.spec_from_file_location("m33", os.path.join(HERE, "33_map.py"))
m33 = importlib.util.module_from_spec(mod)
mod.loader.exec_module(m33)

d = os.path.join(HERE, "..", "metafont-source", "wela")
for fn in sorted(os.listdir(d)):
    if not fn.endswith(("_gr.mf", "_kl.mf", "_sz.mf")):
        continue
    hits = miss = 0
    for line in open(os.path.join(d, fn), encoding="latin-1"):
        if "beginchar" not in line:
            continue
        if m33.BEGIN.search(line):
            hits += 1
        else:
            miss += 1
            if miss <= 6:
                print(f"  MISS {fn}: {line.rstrip()!r}")
    print(f"{fn}: parsed {hits}, missed {miss}")
