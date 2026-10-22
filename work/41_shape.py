#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shape a string with a Schulschriften face's ligature program, no HarfBuzz needed.

HarfBuzz isn't on this box, so the lookups ligatures.py generated get applied
here straight from the .fea text it wrote - which is the same rule set the font
carries. The point is to see what a browser will lay out: a word comes back as
[(glyph name, advance)], forms selected by context and connectors folded in.

The one GSUB rule that shapes the design is modelled explicitly: a lookup may
touch a glyph only once, so each pass walks the string left to right and marks
what it substituted.

Usage: as a module - shape(fea_path, font, text) -> [(name, advance)]
"""
import re
import sys

from fontTools.ttLib import TTFont


def read(fea):
    """The .fea as (substitutions per lookup, position pairs, feature order).

    Accepts a path or the text itself - ligatures.py hands the text straight to
    the shaper when it is only checking a face, not shipping one.
    """
    lines = fea.splitlines() if "\n" in fea else open(fea, encoding="utf-8")
    subs, pos, order, tag = {}, {}, [], None
    look = None
    for line in lines:
        line = line.strip()
        m = re.match(r"lookup (\w+) \{", line)
        if m:
            look = m.group(1)
            subs.setdefault(look, [])
            continue
        m = re.match(r"feature (\w+) \{", line)
        if m:
            tag = m.group(1)
            continue
        m = re.match(r"lookup (\w+);", line)
        if m and tag == "calt":
            order.append(m.group(1))
            continue
        m = re.match(r"sub (.+?) by (.+?);$", line)
        if m and look:
            subs[look].append(_sub(m.group(1), m.group(2)))
            continue
        m = re.match(r"pos (\S+) (\S+) (-?\d+);$", line)
        if m:
            pos.setdefault((m.group(1), m.group(2)), int(m.group(3)))
    return subs, pos, order


def _set(tok):
    """'a' / '[a b c]' -> the set of glyph names that one position accepts"""
    return frozenset(tok[1:-1].split()) if tok.startswith("[") else frozenset([tok])


def _positions(s):
    return [_set(t) for t in re.findall(r"\[[^\]]*\]|\S+", s)]


def _sub(body, result):
    """`bt tgt' la` -> (backtrack, target, lookahead, result, is_ligature)

    Each context item is one glyph position; a bracketed list means any glyph of
    that set, not a run of them.
    """
    if "'" not in body:                       # sub a b by c: a plain ligature
        a, b = body.split()
        return [], _set(a), _positions(b), result, True
    pre, ahead = body.split("'", 1)
    toks = _positions(pre)
    return toks[:-1], toks[-1], _positions(ahead), result, False


def _at(seq, i, names):
    return 0 <= i < len(seq) and seq[i] in names


def apply_lookup(seq, rules):
    """One GSUB pass: left to right, and no glyph is touched twice."""
    done = set()
    i = 0
    while i < len(seq):
        for back, tgt, ahead, result, lig in rules:
            if seq[i] not in tgt or i in done:
                continue
            if not all(_at(seq, i - len(back) + k, b) for k, b in enumerate(back)):
                continue
            if not all(_at(seq, i + 1 + k, a) for k, a in enumerate(ahead)):
                continue
            if lig:
                del seq[i + 1:i + 1 + len(ahead)]
            seq[i] = result
            done.add(i)
            break
        i += 1
    return seq


def shape(fea_path, font, text):
    """[(glyph name, advance)] for `text`, with the joins and the kerns applied."""
    subs, kerns, order = read(fea_path)
    f = TTFont(font) if isinstance(font, str) else font
    cmap, hmtx = f.getBestCmap(), f["hmtx"]
    seq = [cmap[ord(c)] for c in text if ord(c) in cmap]
    for look in order:
        seq = apply_lookup(seq, subs.get(look, []))
    out = []
    for i, name in enumerate(seq):
        value = 0
        if i + 1 < len(seq):
            value = kerns.get((name, seq[i + 1]), 0)
        out.append((name, hmtx[name][0] + value))
    return out


if __name__ == "__main__":
    fea, ttf = sys.argv[1], sys.argv[2]
    text = sys.argv[3] if len(sys.argv) > 3 else "machen"
    for name, adv in shape(fea, ttf, text):
        print(f"  {name:16} {adv}")
