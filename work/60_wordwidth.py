#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Whole words: does the shipped program cost the same as TeX's ligature program?

59_join_audit.py checks one pair at a time. A word is where the chains have to
survive each other - a letter that took a connector from its follower is then
asked for its Endform by the space behind it, and the lookups run in a fixed
order rather than as a program.

Width is the comparison that does not depend on how the folding was done: TeX
lays out a settled glyph list, the font lays out composites, and both have to
come to the same total. A word whose widths differ is a word the web face sets
differently from the LaTeX.

The TeX side runs the *whole* program. The `||` head is METAFONT's boundary of
the input, and these fonts set boundarychar = oct"040", so a word-start rule is
a rule over (space, letter) - the same reading the emitted lookups use, which is
what makes the two sides comparable.

Usage: 60_wordwidth.py ["word"]...
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligatures import MF, SPACE, Face, decorate, resolve

shape = importlib.import_module("41_shape")
FACES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "faces")

WORDS = [" Sieben ", " geben ", " Wasser ", " und aber oder ", " Mutter Kirche ",
         " Afrika? ", " kommst du ", " es war ein Thema ", " Straße ",
         " Häusern ", " überm ", " preußisch ", " quantitativ "]


def program(face):
    index = {}
    for r in face.rules:
        if r.action == "kern":
            continue
        for head in {SPACE if h == -1 else h for h in r.first}:
            index.setdefault((head, r.second), []).append(r)
    return index


def slots(face, text):
    """The character codes TeX would fetch for this text, or None if the face
    cannot set one of the characters (they are compared as the font sets them)."""
    by_name = {face.name_of[c]: c for c in face.codes}
    by_name[face.name_of[SPACE]] = SPACE      # decorate() registered the boundarychar
    cmap = face.ttf.getBestCmap()
    out = []
    for ch in text:
        glyph = cmap.get(ord(ch))
        if glyph is None or glyph not in by_name:
            return None
        out.append(by_name[glyph])
    return out


def main(words):
    bad = 0
    for short in ("su", "dn", "la", "sas", "va"):
        face = Face(os.path.join(FACES, f"entenmann-{short}-regular.ttf"), MF[short])
        decorate(face, verbose=False, label=short)
        index = program(face)
        subs, kerns, order = shape.read(face.fea)
        print(f"--- {short} ---")
        for word in words:
            codes = slots(face, word)
            if codes is None:
                print(f"   {word!r}: the face has no glyph for one of these characters")
                continue
            try:
                settled = resolve(codes, index)
            except RuntimeError as e:
                print(f"   {word!r}: TeX does not settle: {e}")
                bad += 1
                continue
            tex = sum(face.adv(c) for c in settled)
            tex += sum(kerns.get((face.name_of[settled[i]],
                                  face.name_of[settled[i + 1]]), 0)
                       for i in range(len(settled) - 1))
            got_glyphs = shape.shape(face.fea, face.ttf, word)
            got = sum(a for _, a in got_glyphs)
            flag = "" if tex == got else f"   !! off by {got - tex}"
            if tex != got:
                bad += 1
                print(f"   TeX : " + " ".join(f"{face.name_of[c]}" for c in settled))
                print(f"   font: " + " ".join(n for n, _ in got_glyphs))
            print(f"   {word!r:24} TeX={tex:6} font={got:6} "
                  f"glyphs={len(settled)}->{len(got_glyphs)}{flag}")
    print(f"\n{'WORDS MATCH LATEX' if not bad else str(bad) + ' WORDS DIFFER'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or WORDS))
