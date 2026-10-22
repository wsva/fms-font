#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per slot: does the converted face carry the width the tfm says it has?

63_tex_truth.py finds whole words that cost more than they should, and not all of
it is a missing kern. The tfm holds each character's width as TeX lays it out, so
this reads that table and compares it with the advance in the shipped face. A slot
that drifted is a conversion defect that no join can fix.

Usage: 66_tfm_widths.py
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligatures import MF, SPACE, Face, decorate

BUILD = "/tmp/build"
FACES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "faces")


def tfm_widths(tfm):
    """{code: width_in_units_of_1000_em} straight out of the tfm.

    tftopl writes one block per character, and the code is printed as a number in
    octal, decimal or hex - or as the character itself (`C e') when it is printable.
    Reading only the numeric form silently skips the letters, which is where the
    word is made of.
    """
    txt = tfm + ".widths"
    subprocess.run(["tftopl", tfm, txt], check=True, capture_output=True)
    lines = open(txt, encoding="latin-1").read().splitlines()
    os.remove(txt)
    out, code = {}, None
    for line in lines:
        line = line.strip()
        m = re.match(r"\(CHARACTER ([ODHC]) (\S+)\)?\s*$", line)
        if m:
            base = {"O": 8, "D": 10, "H": 16}.get(m.group(1))
            code = int(m.group(2), base) if base else ord(m.group(2)[0])
            continue
        m = re.match(r"\(CHARWD R ([\d.]+)\)\s*$", line)
        if m and code is not None:
            out[code] = round(float(m.group(1)) * 1000)
            code = None
    return out


def main():
    for short in ("su", "dn", "la", "sas", "va"):
        family = MF[short]
        tfm = os.path.join(BUILD, f"trace_{family}14", f"{family}14.tfm")
        widths = tfm_widths(tfm)
        face = Face(os.path.join(FACES, f"entenmann-{short}-regular.ttf"), family)
        decorate(face, verbose=False, label=short)
        bad = []
        for code, want in sorted(widths.items()):
            name = face.name_of.get(code)
            if name is None or name not in face.hmtx.metrics:
                continue
            got = face.hmtx[name][0]
            if abs(got - want) > 1:
                bad.append((f"{code:03o}", name, want, got, got - want,
                            f"{got / want:.4f}"))
        print(f"--- {short}: {len(widths)} slots in the tfm, {len(bad)} drifted")
        for row in bad:
            print("   %s %-16s tfm=%5d face=%5d  off by %+d  ratio %s" % row)


if __name__ == "__main__":
    main()
