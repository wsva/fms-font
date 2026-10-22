#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the LaTeX example PDFs into viewable PNGs.

Usage: 31_pdfrender.py [dpi] [pages]
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "examples_from_latex")
DPI = sys.argv[1] if len(sys.argv) > 1 else "150"
PAGES = sys.argv[2] if len(sys.argv) > 2 else "1-3"

for idx, path in enumerate(sorted(glob.glob(os.path.join(ROOT, "*.pdf"))), 1):
    base = os.path.join(HERE, f"latex{idx}")
    subprocess.run(["pdftoppm", "-png", "-r", DPI, "-f", PAGES.split("-")[0],
                    "-l", PAGES.split("-")[-1], path, base], check=True)
    for png in sorted(glob.glob(base + "*.png")):
        print(os.path.relpath(png, os.path.join(HERE, "..")), os.path.getsize(png))
