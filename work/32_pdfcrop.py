#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crop one band out of a LaTeX example page at high resolution.

Usage: 32_pdfcrop.py <pdf_index> <page> <dpi> <y_pt> <h_pt> <out.png>
y_pt/h_pt are in PDF points from the top of the page so a line can be selected
without knowing the pixel geometry.
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "examples_from_latex")

idx, page, dpi, y_pt, h_pt, out = sys.argv[1:7]
pdf = sorted(glob.glob(os.path.join(ROOT, "*.pdf")))[int(idx) - 1]
y = int(float(y_pt) * int(dpi) / 72)
h = int(float(h_pt) * int(dpi) / 72)
base = os.path.join(HERE, out)
subprocess.run(["pdftoppm", "-png", "-r", dpi, "-f", page, "-l", page,
                "-y", str(y), "-x", "0", "-H", str(h), "-W", "100000", pdf, base],
               check=True)
for png in sorted(glob.glob(base + "*.png")):
    print(os.path.basename(png), os.path.getsize(png))
