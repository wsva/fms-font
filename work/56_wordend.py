#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Where did the word-end forms go?

METAFONT ends a word in two steps (`% Wortende erkennen` in wela14_lig.mf):

    oct"040" |=:| oct"006"      a + space  ->  a  marker  space
    oct"006" =:| oct"241"       a + marker ->  Endform(a)  marker

So the pair (letter, space) has to be enumerated, and its output is a *left* form
whose result is the composite Endform+marker. If a generated .fea has no rule with
`space` as lookahead, one of the two steps got lost on the way.

This reports, for one face, exactly which of the four things the chain needs is
missing: the space glyph, SPACE in the enumeration, the parse of the two rules,
and the resolution of the pair.

Usage: 56_wordend.py <in.ttf> [letter]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligparse import START
from ligatures import MF, Face, SPACE, analyse, decorate, resolve


def main(path, letter="a"):
    from fontTools.ttLib import TTFont
    raw = TTFont(path)
    order = raw.getGlyphOrder()
    print(f"{os.path.basename(path)}: {len(order)} glyphs, "
          f"'space' in glyf: {'space' in order}")

    face = Face(path, MF[os.path.basename(path).split("-")[1]])
    print(f"family={face.family} codes={len(face.codes)} typed={len(face.typed)} "
          f"SPACE in typed(before add_space): {SPACE in face.typed}")

    face.add_space()
    print(f"after add_space: SPACE in typed: {SPACE in face.typed}, "
          f"typed={len(face.typed)}, name_of[32]={face.name_of.get(SPACE)}")
    for c in (0, 6, 8, 32, ord(letter)):
        nm = face.name_of.get(c)
        w = face.codes.get(c)
        adv = face.hmtx[nm][0] if nm in face.glyf.keys() else None
        print(f"  code {c:03o} {nm or '-':16} source={w} advance={adv}")

    # the two chain rules, straight out of the parser
    key = ord(letter)
    hits = [r for r in face.rules if key in r.first and r.second in (SPACE, 6, 8)]
    print(f"rules with head {letter}: {len(hits)}")
    for r in hits:
        print("   ", r)

    index = {}
    for r in face.rules:
        if r.action == "kern" or r.word_start:
            continue
        for head in r.first:
            index.setdefault((head, r.second), []).append(r)
    res = resolve([key, SPACE], index)
    print("resolve([%s, space]) ->" % letter, " ".join(f"{c:03o}" for c in res))

    if SPACE not in face.typed:
        face.typed.append(SPACE)
        face.typed.sort()
        print(">> forced SPACE into typed (what a pristine face gets for free)")
    alphabet, right_forms, left_forms, ligatures, ambiguous = analyse(face)
    with_space = {k: v for k, v in left_forms.items() if SPACE in v}
    print(f"left_forms={len(left_forms)} of which space-triggered: {len(with_space)}")
    for (x, head), contexts in sorted(with_space.items())[:8]:
        print(f"   {face.name_of[x]}' + space -> {face.glyph_for(head)}")

    # the real generator, on the same face - this is what a rebuild would ship
    decorate(face, verbose=True, label=os.path.basename(path))
    fea = face.fea
    hits = [ln.strip() for ln in fea.splitlines()
            if chr(39) + " space" in ln or chr(39) + " [" in ln and "space" in ln]
    print(f"rules with a space lookahead: {len(hits)}")
    for ln in hits[:5]:
        print("   ", ln)
    print("WordJoins lookups:",
          sum(1 for ln in fea.splitlines() if ln.startswith("lookup WordJoins")))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "a")
