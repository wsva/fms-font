#!/usr/bin/env python3
"""Per-glyph: tfm width vs the face's advance, for one word's TeX glyph list."""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligatures import MF, SPACE, Face, decorate
shape = __import__("importlib").import_module("41_shape")

BUILD = "/tmp/build"
FACES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "faces")
short, word = sys.argv[1], sys.argv[2]
family = MF[short]
tfm = os.path.join(BUILD, f"trace_{family}14", f"{family}14.tfm")
txt = "/tmp/tfm.txt"
subprocess.run(["tftopl", tfm, txt], check=True, capture_output=True)
text = open(txt, encoding="latin-1").read()

# (CHARACTER O 144 / (CHARACTER C o  followed by (CHARWD R w) - the number format
# letter tells how to read the code, C means the character itself.
widths, code = {}, None
for line in text.splitlines():
    line = line.strip()
    m = re.match(r"\(CHARACTER ([OCHD]) (\S+)\)?\s*$", line)
    if m:
        base = {"O": 8, "D": 10, "H": 16}.get(m.group(1))
        code = int(m.group(2), base) if base else ord(m.group(2)[0])
        continue
    m = re.match(r"\(CHARWD R ([\d.]+)\)\s*$", line)
    if m and code is not None:
        widths.setdefault(code, round(float(m.group(1)) * 1000))

face = Face(os.path.join(FACES, f"entenmann-{short}-regular.ttf"), family)
decorate(face, verbose=False, label=short)
code_of = {face.name_of[c]: c for c in face.codes}
code_of[face.name_of[SPACE]] = SPACE
name_of_code = face.name_of

print(f"word {word!r}")
tot_t = tot_f = 0
for name, adv in shape.shape(face.fea, face.ttf, " " + word + " "):
    if name.startswith("p") and re.fullmatch(r"p\d{3}(_\d{3})+", name):
        parts = [int(p, 8) for p in name[1:].split("_")]
    else:
        parts = [code_of[name]]
    t = sum(widths.get(p, -1) for p in parts)
    if name != "space":
        tot_t += t
        tot_f += adv
    each = " ".join(f"{oct(p)}:tfm={widths.get(p, -1)}/face={face.adv(p) if p in face.name_of and face.name_of[p] in face.hmtx.metrics else '?'}"
                    for p in parts)
    print(f"   {name:14} {each} composite_face={adv}")
print(f"   interior tfm={tot_t} face={tot_f}")
