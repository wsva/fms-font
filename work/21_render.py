#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a string through FontForge's own shaper, straight from a face file.

Bounding-box arithmetic (13_metrics.py / 18_follow.py) can only say where two
glyphs' boxes overlap - it cannot say whether any *ink* collides, which is what
the eye reports. This rasterises real text with the font's own advances, so the
result can be looked at.

Usage: FONT=/tmp/x.ttf OUT=/tmp/x.png TEXT=... fontforge -lang=py work/21_render.py

Arguments are taken from the environment because FontForge's python launcher
keeps its own argv and does not hand the script's trailing words over reliably.
"""
import os

import fontforge

path = os.environ["FONT"]
size = float(os.environ.get("SIZE", 72))
out = os.environ.get("OUT", "/tmp/render.png")
text = os.environ.get("TEXT", "Fremdsprachen machen Spa\u00df")

font = fontforge.open(path)
bitmap = font.renderString(text, size)
bitmap.save(out, size, 1)
print(f"rendered {path} -> {out} ({bitmap.width}x{bitmap.height})")
