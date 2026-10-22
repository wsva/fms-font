#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Let TeX set the same words the browser sets, so the two can be looked at.

72_browser_truth.html and 63_tex_truth.py both compare *numbers*. This makes a
picture: one TeX box per word, fed through \char so the tfm's own ligature/kern
program decides the glyphs, at the same em size as the browser page. Whatever
difference survives is one you can see, and the standing rule is that metrics are
not proof - rendering is.

One PNG per family, cropped to a page that is only as tall as its own lines, so
73_render_proof.html can drop each one straight above the browser's rendering of
the same text and the two read line against line.

Usage: 74_tex_words.py            (writes ../work/tex_words_<family>.png)

DOES NOT WORK, kept so the reason is not rediscovered: mftrace's .pfa cannot be
used as a TeX text font. Its Encoding and CharStrings do not pair up the way the
tfm slots read, so dvips paints the right glyph at the wrong code - the output is
garbage at every size, and `\char` and literal text are garbage in exactly the
same way, which is the probe that proves it is the font and not the codes.
FontForge maps glyphs by *name* when it builds the TTFs, which is why those are
correct and this is not. The LaTeX renderings that do exist are
../schulschriften.pdf (pages 17-21 are the five Musterblaetter, each titled with
its own script as a connected word) and ../examples_from_latex/; 75_latex_pairs.html
compares those against the faces, which is the picture this was meant to make.
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligatures import MF, SPACE, Face

HERE = os.path.dirname(os.path.abspath(__file__))
FACES = os.path.join(HERE, "..", "faces")
BUILD = "/tmp/build"
TYPE1 = "/tmp/type1"
OUT = "/tmp/tex_words"
DPI = 150

#: the browser sets its word lines at 66px per em, so TeX sets them at the
#: point size that comes out 66px tall at this resolution
EM_PT = 66 * 72 / DPI

SENT = ["Wo ist die Schweiz? Wo ist Oesterreich?",
        "Das ist Martin Mueller aus Australien."]
WORDS = ["Sieben", "geben", "Mutter", "Straße", "quantitativ", "Papier"]
FAMILIES = ["la", "su", "dn", "sas", "va"]


def codes_of(face, cmap, word):
    """The tfm slots behind a word, as the face's own cmap sees them."""
    out = []
    for ch in word:
        g = cmap.get(ord(ch))
        if g is None or g not in face.code_of:
            raise SystemExit(f"no glyph for {ch!r} in {word!r}")
        out.append(face.code_of[g])
    return out


def pfb(name):
    """The binary Type1 dvips wants, from the .pfa mftrace left beside the tfm.

    dvips will not read ASCII .pfa, and when it cannot find a font it substitutes
    another one and carries on, so the caller checks the PostScript for the
    substitution rather than trusting the exit status.
    """
    os.makedirs(TYPE1, exist_ok=True)
    dst = os.path.join(TYPE1, name + ".pfb")
    if not os.path.exists(dst):
        src = os.path.join(BUILD, f"trace_{name}", name + ".pfa")
        # t1binary, not t1asm: t1asm assembles a plainfont and finds no charstrings
        # in a .pfa, leaving a font file dvips quietly substitutes
        subprocess.run(["t1binary", src, dst], check=True)
    return dst


def build(short):
    """TeX -> dvi -> ps -> pdf -> png for one family's block."""
    face = Face(os.path.join(FACES, f"entenmann-{short}-regular.ttf"), MF[short])
    face.code_of = {face.name_of[c]: c for c in face.codes}
    face.code_of[face.name_of[SPACE]] = SPACE
    cmap = face.ttf.getBestCmap()

    lines = [r"\hsize=10.5in \vsize=5in \parindent=0pt \parskip=5pt",
             r"\special{papersize=11in,5.2in}"]
    for text in SENT + WORDS:
        chars = "".join(f"\\char{c}" for c in codes_of(face, cmap, text))
        # \font is forbidden inside a \def, so the switch is written out per line
        lines.append(r"{\font\f=%s14 at %.2fpt \f %s\par}" % (MF[short], EM_PT, chars))
    with open(os.path.join(OUT, "words.tex"), "w") as fh:
        fh.write("\n".join(lines) + "\n\\bye\n")

    name = MF[short] + "14"
    pfb(name)
    # a map line with no `<enc` keeps the font's own encoding, which is the one
    # mftrace wrote from this very tfm - so the \char slots land where TeX put them
    with open(os.path.join(OUT, "words.map"), "w") as fh:
        fh.write(f"{name} {name}.pfb\n")

    # dvips looks the -u map up through kpathsea, not in the working directory, so
    # the run dir has to be on DVIPSHEADERS or the map is silently ignored and a
    # bitmap of cmr10 is substituted for the traced font
    env = dict(os.environ, TFMFONTS=f":{BUILD}//", T1FONTS=f":{TYPE1}//",
               TEXPSHEADERS=f":{BUILD}//", DVIPSHEADERS=f":{OUT}:{BUILD}//")
    subprocess.run(["tex", "-interaction=batchmode", "words.tex"],
                   cwd=OUT, env=env, capture_output=True)
    log = open(os.path.join(OUT, "words.log"), encoding="latin-1").read()
    if any(l.startswith("!") for l in log.splitlines()):
        print("\n".join(l for l in log.splitlines() if l.startswith("!")))
        raise SystemExit(f"{short}: TeX failed - see /tmp/tex_words/words.log")
    for cmd in (["dvips", "-q", "-u", "words.map", "-o", "words.ps", "words.dvi"],
                ["ps2pdf", "words.ps", "words.pdf"],
                ["pdftoppm", "-png", "-r", str(DPI), "-singlefile", "words.pdf", "words"]):
        got = subprocess.run(cmd, cwd=OUT, env=env, capture_output=True, text=True)
        # dvips exits 0 even when it could not load a font - it prints the
        # substitution to stderr and carries on with a bitmap of another one
        if got.returncode or "not found" in got.stderr or "mismatch" in got.stderr:
            print(got.stderr[-1500:])
            raise SystemExit(f"{short}: {' '.join(cmd)} could not use {name}.pfb")

    dst = os.path.join(HERE, f"tex_words_{short}.png")
    shutil.copyfile(os.path.join(OUT, "words.png"), dst)
    return dst


def main():
    os.makedirs(OUT, exist_ok=True)
    for short in FAMILIES:
        print("wrote", build(short))


if __name__ == "__main__":
    main()
