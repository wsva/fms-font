#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report what the LaTeX-produced example PDFs actually contain.

These are the ground truth: they were typeset with the real METAFONT fonts and
the tfm ligature program, so whatever the web conversion is missing has to be
visible here. Which fonts got embedded, and what the page says, are the two
questions this answers; the images are rendered separately.
"""
import glob
import os
import subprocess

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples_from_latex")


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return (p.stdout + p.stderr).strip()


for path in sorted(glob.glob(os.path.join(ROOT, "*.pdf"))):
    print("=" * 70)
    print(os.path.basename(path))
    info = run(["pdfinfo", path]).splitlines()
    for line in info:
        if line.split(":", 1)[0] in ("Pages", "Page size", "Creator", "Producer", "Title"):
            print("  ", line)
    print("--- fonts ---")
    print(run(["pdffonts", path]))
