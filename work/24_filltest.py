#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit-test the scanline fill of 22_inkrender.py against shapes with a known area.

Usage: 24_filltest.py
"""
import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "inkrender", os.path.join(os.path.dirname(__file__), "22_inkrender.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def count(polys, w, h, sx, sy, baseline):
    mask = [[0] * w for _ in range(h)]
    m.fill(mask, polys, w, h, sx, sy, baseline)
    return sum(sum(r) for r in mask), mask


# A 10x10 square drawn at 1:1 with the baseline at the bottom row.
box = [(2, 0), (12, 0), (12, 10), (2, 10)]
n, mask = count([box], 20, 20, 1.0, 1.0, 20)
print(f"square 10x10 -> {n} pixels (expect ~100)")
for y, row in enumerate(mask):
    print(f"  {y:>2} {''.join('#' if v else '.' for v in row)}")

# The same square scaled to 0.5 px per unit: area ~25.
n2, _ = count([box], 20, 20, 0.5, 0.5, 20)
print(f"square at half scale -> {n2} pixels (expect ~25)")
