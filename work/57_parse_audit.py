#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Does the parser see every entry the .mf file writes?

ligtable programs are not all plain `head: pattern action result` lists. weva
uses METAFONT's labelled-program form (`1:: ... skipto 1`), and a parser that
only understands the plain form silently drops everything after the label - both
the kerns and, worse, the substitutions in the same table.

`ligatures.Face` now refuses to build on a shortfall; this reports the numbers
per action so a loss can be located, not just noticed.

Usage: 57_parse_audit.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligparse import LIG_OPS, count_entries, parse_lig

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "metafont-source")
ACTIONS = {(False, False): "=:", (False, True): "=:|",
           (True, False): "|=:", (True, True): "|=:|"}


def parsed_actions(rules):
    out = {}
    for r in rules:
        key = "kern" if r.action == "kern" else ACTIONS[r.action]
        out[key] = out.get(key, 0) + 1
    return out


for family in ("wesu", "wedn", "wela", "wesa", "weva"):
    path = os.path.join(SRC, family, f"{family}14_lig.mf")
    src = count_entries(path)
    got = parsed_actions(parse_lig(path))
    print(f"{family}: source entries={sum(src.values())}  parsed={sum(got.values())}"
          + ("   <-- LOSS" if sum(src.values()) != sum(got.values()) else ""))
    for op in LIG_OPS + ("kern",):
        s, g = src.get(op, 0), got.get(op, 0)
        print(f"    {op:6} source={s:4} parsed={g:4}" + ("" if s == g else "   !!"))
