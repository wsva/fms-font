#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Where does a kern TeX applied actually sit, and what does the face have there?

63_tex_truth.py says whole words are too wide by exactly the kerns TeX reports, but
a kern is a junction, and a junction is a pair of *glyph names* by the time the face
lays it out: the program may have changed either letter into another form, or folded
a connector into it as a composite. `pos a b -250` written against the base letters
then matches nothing.

This walks TeX's own box dump, attributes every kern node to the junction it follows,
and reports what the shipped lookups put at that same junction and whether the
translated .fea has a `pos` for that name pair. That is the difference between a
kern that is missing from the font and a kern that is there under the wrong name.

Usage: 70_kern_junction.py <family short> <word>
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligatures import MF, SPACE, Face, decorate

shape = __import__("importlib").import_module("41_shape")
HERE = os.path.dirname(os.path.abspath(__file__))
FACES = os.path.join(HERE, "..", "faces")
BUILD = "/tmp/build"


def tex_box(family, codes):
    """TeX's settled list as [(kind, payload)]: ('g', code) or ('k', units)."""
    tfm = os.path.join(BUILD, f"trace_{family}14", f"{family}14.tfm")
    txt = "/tmp/tfm_k.txt"
    subprocess.run(["tftopl", tfm, txt], check=True, capture_output=True)
    design = float(re.search(r"\(DESIGNSIZE R ([\d.]+)\)",
                             open(txt, encoding="latin-1").read()).group(1))
    chars = "".join(f"\\char{c}" for c in codes)
    workdir = "/tmp/tex_kern"
    os.makedirs(workdir, exist_ok=True)
    tex = os.path.join(workdir, "k.tex")
    with open(tex, "w") as fh:
        fh.write("\\showboxdepth=100 \\showboxbreadth=5000\n"
                 "{\\font\\f=%s14 at %spt \\f\\setbox0=\\hbox{%s}\\showbox0\\relax}\n"
                 "\\message{done}\n" % (family, design, chars))
    env = dict(os.environ, TFMFONTS=f":{os.path.dirname(tfm)}//", TEXINPUTS=":")
    subprocess.run(["tex", "-interaction=batchmode", "k.tex"], cwd=workdir,
                   env=env, capture_output=True)
    log = open(os.path.join(workdir, "k.log"), encoding="latin-1").read()
    if "not loadable" in log:
        raise SystemExit(f"{family}14.tfm not loadable")
    out = []
    for line in log.splitlines():
        line = line.strip()
        m = re.match(r"\.\\kern(-?[\d.]+)", line)
        if m:
            out.append(("k", round(float(m.group(1)) * 1000 / design)))
            continue
        m = re.match(r"\.\\f\s+(\S+)(?:\s+\(ligature (\S*)\))?", line)
        if m:
            out.append(("g", _decode(m.group(1))))
    return out


def _decode(tok):
    if tok.startswith("^^"):
        rest = tok[2:]
        return 127 if rest == "?" else (ord(rest) - 64 if len(rest) == 1
                                        else int(rest, 16))
    return ord(tok)


def unfold(face, name):
    """A font glyph name -> the tfm codes it now stands for."""
    if name.startswith("p") and re.fullmatch(r"p(?:\d{3})(?:_\d{3})+", name):
        return [int(part, 8) for part in name[1:].split("_")]
    return [face.code_of[name]]


def main(short, word):
    if word == "all":
        # ß and ü do not survive a PowerShell -> WSL argument, so the corpus lives
        # here rather than on the command line
        for w in ("Sieben", "geben", "Wasser", "und aber oder", "Mutter Kirche",
                  "Afrika?", "kommst du", "es war ein Thema", "Straße", "Häusern",
                  "überm", "preußisch", "quantitativ", "auf", "dem Tisch", "zwei"):
            for part in w.split():
                try:
                    report(short, part)
                except (KeyError, IndexError) as e:
                    print(f"{short} {part!r}: no glyph for {e}")
        return
    report(short, word)


def report(short, word):
    family = MF[short]
    face = Face(os.path.join(FACES, f"entenmann-{short}-regular.ttf"), family)
    decorate(face, verbose=False, label=short)
    code_of = {face.name_of[c]: c for c in face.codes}
    code_of[face.name_of[SPACE]] = SPACE
    face.code_of = code_of
    cmap = face.ttf.getBestCmap()
    codes = [code_of[cmap[ord(ch)]] for ch in word]

    # every kern the translated program wrote, keyed by the name pair it targets
    fea_pos = {}
    for m in re.finditer(r"^\s*pos (\S+) (\S+) (-?\d+);", face.fea, re.M):
        fea_pos.setdefault((m.group(1), m.group(2)), []).append(int(m.group(3)))
    # and every kern the .mf declares, keyed by the code pair
    mf_kerns = {}
    for r in face.rules:
        if r.action != "kern":
            continue
        ut = face.kvars[r.result] if isinstance(r.result, str) else r.result
        for head in r.first:
            mf_kerns.setdefault((head, r.second), []).append(round(face.scale * ut))

    got = shape.shape(face.fea, face.ttf, " " + word + " ")[1:-1]
    quiet = bool(os.environ.get("QUIET"))
    if not quiet:
        print(f"{short} {word!r}")
        print("   font glyph list:", " ".join(f"{n}({a})" for n, a in got))
    # TeX's glyph entries and the font's unfolded codes are the same list (63 checks
    # that), so a kern node between TeX entries i and i+1 belongs to the font glyph
    # that covers code i on its left and the one that covers code i+1 on its right.
    flat = [name for name, _ in got for _ in unfold(face, name)]
    box = tex_box(family, codes)
    if not quiet:
        print("   TeX box:", " ".join(f"{p:03o}" if k == "g" else f"k{p:+}"
                                      for k, p in box))
    gi = -1
    junctions = []
    for kind, payload in box:
        if kind == "g":
            gi += 1
        else:
            left, right = (flat[gi], flat[gi + 1]) if gi + 1 < len(flat) \
                else ("?", "?")
            junctions.append((payload, left, right, gi))
    if quiet:
        if junctions:
            print(f"   {word!r:14}" + "".join(
                f"  {l}|{r} {v:+} {'INNER' if l == r else ('fea' if fea_pos.get((l, r)) else 'MISSING')}"
                for v, l, r, _ in junctions))
        return
    print("   kerns TeX applied, and where the face can put them:")
    for value, left, right, i in junctions:
        same = left == right
        print(f"      after entry {i}: {left} | {right}  {value:+5}"
              f"   fea pos: {fea_pos.get((left, right))}"
              f"{'   (inside one composite)' if same else ''}")
    return


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "all")
