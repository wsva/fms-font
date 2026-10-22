#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which METAFONT character ended up in which TTF glyph.

The wela sources cut a second, narrower form of nearly every letter (oct 241..
for the lowercase, oct 201.. for the capitals) plus a run of connector glyphs in
the control-code slots, and the tfm ligature program picks between them. mftrace
named the slots from tex256.enc, so in the converted face those forms are
hiding under names like "exclamdown" and "ccaron". This pairs each beginchar in
the sources with the glyph sitting at that slot and checks the advance width, so
the identity of every one of them is established by measurement rather than by
guessing at a name.

Usage: 33_map.py <ttf> [family_dir]
"""
import os
import re
import sys

from fontTools.ttLib import TTFont

ENC_PATH = "/usr/share/texlive/texmf-dist/fonts/enc/dvips/base/tex256.enc"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "metafont-source")

BEGIN = re.compile(r'beginchar\(\s*(oct"[0-7]+"|"(?:\\")|[^,)]+?)\s*,\s*([\d.]+)\s*ut#')


def enc_slots(path):
    """tex256.enc -> {slot: glyph name}.

    The array is positional - /T1Encoding [ /grave /acute ... ] def - so the
    slot number is the index, and the "% 0" comments are only annotations.
    """
    text = open(path, encoding="latin-1").read()
    body = text[text.index("[") + 1:text.rindex("]")]
    body = re.sub(r"%[^\n]*", "", body)
    names = body.split()
    assert len(names) == 256, f"{path}: {len(names)} entries, expected 256"
    return {i: n.lstrip("/") for i, n in enumerate(names)}


def mf_chars(dirname):
    """[(code, predicted width in ut#)] in source order, for one family."""
    out = []
    d = os.path.join(SRC, dirname)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith("_gr.mf") and not fn.endswith("_kl.mf") and not fn.endswith("_sz.mf"):
            continue
        for line in open(os.path.join(d, fn), encoding="latin-1"):
            m = BEGIN.search(line)
            if not m:
                continue
            tok, w = m.group(1), float(m.group(2))
            if tok.startswith('oct"'):
                code = int(tok[4:-1], 8)
            elif tok.startswith('"'):
                code = ord(tok[1])
            else:
                continue
            out.append((code, w, fn))
    return out


def main():
    ttf = sys.argv[1]
    dirname = sys.argv[2] if len(sys.argv) > 2 else "wela"
    slots = enc_slots(ENC_PATH)
    f = TTFont(ttf)
    hmtx = f["hmtx"]
    order = [g for g in f.getGlyphOrder() if g not in (".notdef", ".null", "nonmarkingreturn")]
    by_name = {n: hmtx[n][0] for n in order}

    chars = mf_chars(dirname)
    print(f"{len(chars)} beginchar in {dirname}, {len(order)} glyphs in {os.path.basename(ttf)}")
    scale = by_name["A"] / dict((c, w) for c, w, _ in chars)[ord("A")]
    print(f"scale = {scale:.4f} font units per ut#\n")

    unmatched = 0
    for code, w, fn in sorted(chars):
        name = slots.get(code, "?")
        got = by_name.get(name)
        want = round(w * scale)
        print(f"  oct{code:03o} {code:>3} {name:<16} adv={str(got):<5} want~{want:<5} [{fn[:-3]}]")
        if got is None or abs(got - want) > max(3, 0.02 * want):
            unmatched += 1
    print(f"\n{unmatched} of {len(chars)} slots missing or width-mismatched")

    print("glyphs not reachable from any beginchar:",
          sorted(set(order) - {slots.get(c) for c, _w, _f in chars}))


if __name__ == "__main__":
    main()
