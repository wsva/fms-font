#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every pair the tfm program changes must change in the shipped lookups too.

`resolve()` is TeX: it applies the ligtable program to a glyph list.
`apply_lookup()` is the OpenType translation of the same program, run over the
.fea text the build wrote into the face. This feeds both the same pair and asks
whether they agree.

A pair where they disagree is a join the browser will not make - either the rule
never got emitted, or an earlier lookup destroyed the context the rule needed.

TeX leaves an inserted connector as its own glyph; GSUB cannot insert, so the
translation folds a run of output glyphs into a composite on its left. `fold()`
applies exactly that convention to TeX's answer to make the two comparable.

Usage: 59_join_audit.py [family]...
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligatures import MF, SPACE, Face, decorate, resolve

shape = importlib.import_module("41_shape")
FACES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "faces")


def program(face):
    index = {}
    for r in face.rules:
        if r.action == "kern" or r.word_start:
            continue
        for head in r.first:
            index.setdefault((head, r.second), []).append(r)
    return index


def fold(face, res):
    """TeX's settled code list -> the glyph sequence the font has to produce."""
    if len(res) == 1:
        return [face.name_of[res[0]]]
    return [face.glyph_for(res[:-1]), face.name_of[res[-1]]]


def main(families):
    total_wrong = 0
    for short in families:
        face = Face(os.path.join(FACES, f"entenmann-{short}-regular.ttf"), MF[short])
        decorate(face, verbose=False, label=short)
        index = program(face)
        subs, _kerns, order = shape.read(face.fea)

        pairs = [(x, y) for x in face.typed for y in face.typed]
        changed, wrong = [], []
        for x, y in pairs:
            try:
                res = resolve([x, y], index)
            except RuntimeError:
                res = None
            if not res or res == [x, y]:
                continue
            changed.append((x, y))
            want = fold(face, res)
            seq = [face.name_of[x], face.name_of[y]]
            for look in order:
                seq = shape.apply_lookup(seq, subs.get(look, []))
            if seq != want:
                wrong.append((x, y, want, seq))
        ends = sum(1 for x, y in changed if y == SPACE)
        total_wrong += len(wrong)
        print(f"{short}: {len(pairs)} pairs, {len(changed)} the program changes "
              f"({ends} of them a word end), {len(wrong)} disagree")
        for x, y, want, got in wrong[:12]:
            print(f"    {face.name_of[x]} + {face.name_of[y]}:  TeX -> "
                  f"{'/'.join(want)}   font -> {'/'.join(got)}")
    print(f"{'ALL FAMILIES AGREE' if not total_wrong else str(total_wrong) + ' PAIRS DISAGREE'}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["su", "dn", "la", "sas", "va"])
