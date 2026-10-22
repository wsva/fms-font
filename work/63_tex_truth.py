#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Do the web faces lay a word out the way TeX does? Ground truth: TeX itself.

59_join_audit.py compares one pair at a time and 60_wordwidth.py compares my
re-reading of the .mf, but both judge the font against a model. The METAFONT run
that made the traces also made the .tfm files, and a .tfm holds the ligature/kern
program *as TeX compiled it*. So this asks TeX: put the character codes of a word
into an \hbox, dump the box, and read off the glyph list and the width TeX settled
on. That is the answer the web face has to reproduce.

The comparison is per code, not per glyph name, because a connector cannot be
inserted by GSUB: the font folds it into the glyph on its left as a composite
whose name records the codes it covers (p000_005 = slots 0 and 5). Unfolding the
composites has to give exactly TeX's list, and the summed advances have to give
exactly TeX's width.

TeX ends a character list with the boundarychar in effect, so a word with no
spaces around it still gets its Anfangs- and Endform - and the face needs a real
space glyph for both, which is why the font side is padded and unpadded here.

Two deviations are allowed for, because they are design rather than damage:

  * The face's own advances are integers and the tfm's are not, so a composite is
    the sum of the rounded parts while TeX rounds once at the end - a few units.
  * e_overhang.py widens the lowercase glyphs whose ink overruns their advance, so
    that the next letter does not paint over them. That is a deliberate departure
    from the charwd, so the width test compares TeX's box with TeX's width *plus*
    the same repair, read off the face itself.

Anything left over is a junction whose kern the program lost.

Usage: 63_tex_truth.py [word]...     (words as typed; codes come from the face)
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
WORK = "/tmp/tex_truth"

#: the face adds up rounded advances and TeX rounds once at the end, so a word of
#: n glyphs may differ from TeX's box by up to n units without anything being wrong
TOLERANCE = 12

#: the kerns this program carries sit on the junctions to dots and accents (an `i'
#: is drawn as its body plus a separate dot glyph the kern pulls back), so the
#: corpus has to cover dotted and accented letters next to the join forms.
WORDS = ["Sieben", "geben", "Wasser", "und aber oder", "Mutter Kirche",
         "Afrika?", "kommst du", "es war ein Thema", "Straße", "Häusern",
         "überm", "preußisch", "quantitativ", "auf", "dem Tisch", "zwei",
         "Mit bitte", "i I j J", "Ärger Öfen Übe", "Wieder Spiel", "Küche Bücher",
         "Möwe Würfel", "Indien Ideal", "Zinnober", "Sprache Geschichte",
         "Freundschaft", "Zeitung Papier", "Blut Silber Gold", "Laterne Wiese"]


def design_size(tfm):
    """DESIGNSIZE of a tfm - the size at which one em is the tfm's units."""
    txt = tfm + ".txt"
    subprocess.run(["tftopl", tfm, txt], check=True, capture_output=True)
    out = open(txt, encoding="latin-1").read()
    os.remove(txt)
    return float(re.search(r"\(DESIGNSIZE R ([\d.]+)\)", out).group(1))


def tex_lists(family, jobs):
    """Ask TeX for the settled glyph list of each code list.

    `jobs` is [(label, codes)]. Returns {label: (codes, width_in_em_units)}.
    """
    tfm = os.path.join(BUILD, f"trace_{family}14", f"{family}14.tfm")
    design = design_size(tfm)
    lines = [r"\showboxdepth=100 \showboxbreadth=5000"]
    for i, (_, codes) in enumerate(jobs):
        chars = "".join(f"\\char{c}" for c in codes)
        lines.append("{\\font\\f=%s14 at %spt \\f \\setbox0=\\hbox{%s}"
                     "\\message{@%d \\the\\wd0}\\showbox0\\relax}"
                     % (family, design, chars, i))
    os.makedirs(WORK, exist_ok=True)
    tex = os.path.join(WORK, family + ".tex")
    with open(tex, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    env = dict(os.environ, TFMFONTS=f":{os.path.dirname(tfm)}//", TEXINPUTS=":")
    subprocess.run(["tex", "-interaction=batchmode", os.path.basename(tex)],
                   cwd=WORK, env=env, capture_output=True)
    log = open(os.path.join(WORK, family + ".log"), encoding="latin-1").read()
    if "not loadable" in log:
        raise SystemExit(f"{family}14.tfm not found - TeX set nothing (see {WORK})")

    # batchmode writes the log as one stream: a \message arrives glued to whatever
    # line it interrupted (`(./wesu.tex @0 2.796pt`), and the box dump follows on
    # whole lines. So the messages are found by searching, the entries by prefix.
    msg = re.compile(r"@(\d+) (-?[\d.]+)pt")
    glyph = re.compile(r"^\.\\f\s+(\S+)")
    kern = re.compile(r"^\.\\kern(-?[\d.]+)")
    out, label, codes_seen, kerns_seen, width = {}, None, [], [], None
    for line in log.splitlines():
        line = line.strip()
        for m in msg.finditer(line):
            if label is not None:
                out[label] = (codes_seen, kerns_seen, width)
            label = int(m.group(1))
            codes_seen, kerns_seen, width = [], [], float(m.group(2))
        if label is None:
            continue
        m = kern.match(line)
        if m:
            kerns_seen.append(round(float(m.group(1)) * 1000 / design))
            continue
        m = glyph.match(line)
        if m:
            codes_seen.append(_decode(m.group(1)))
    if label is not None:
        out[label] = (codes_seen, kerns_seen, width)
    return {k: (v[0], v[1], round(v[2] * 1000 / design)) for k, v in out.items()}


def _decode(tok):
    """TeX's show output escapes a char as itself, as ^^X (< 32) or as ^^hh (>= 128)."""
    if tok.startswith("^^"):
        rest = tok[2:]
        if len(rest) == 1:
            return 127 if rest == "?" else ord(rest) - 64
        return int(rest, 16)
    return ord(tok)


def unfold(face, name):
    """A font glyph name -> the tfm codes it now stands for."""
    if name.startswith("p") and re.fullmatch(r"p(?:\d{3})(?:_\d{3})+", name):
        return [int(part, 8) for part in name[1:].split("_")]
    return [face.code_of[name]]


def tfm_widths(tfm):
    """{code: CHARWD in units of a 1000 em}, straight out of the tfm.

    tftopl writes one block per character and prints the code as a number in
    octal, decimal or hex - or as the character itself (`C e') when it is
    printable, which is where most of the word is.
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


def font_list(face, word):
    """[(name, advance)] the shipped lookups produce, with the padding removed.

    The face has to be padded because GSUB has no notion of a word boundary: a
    space glyph is the only thing that can open or close a word for it, whereas
    TeX pads every character list with the boundarychar by itself.
    """
    got = shape.shape(face.fea, face.ttf, " " + word + " ")
    if got[0][0] != "space" or got[-1][0] != "space":
        raise AssertionError(f"{word!r}: the padding did not survive: {got}")
    return got[1:-1]


def main(words, json_out=None):
    bad = []
    table = {}
    for short in ("su", "dn", "la", "sas", "va"):
        face = Face(os.path.join(FACES, f"entenmann-{short}-regular.ttf"), MF[short])
        decorate(face, verbose=False, label=short)
        face.code_of = {face.name_of[c]: c for c in face.codes}
        face.code_of[face.name_of[SPACE]] = SPACE
        cmap = face.ttf.getBestCmap()

        # one TeX box per word: the phrases in the list are split, a space is
        # where TeX would have started a new word anyway
        jobs, kept = [], []
        for phrase in words:
            for word in phrase.split():
                codes, ok = [], True
                for ch in word:
                    g = cmap.get(ord(ch))
                    if g is None or g not in face.code_of:
                        print(f"--- {short}: skipping {word!r}, no glyph for {ch!r}")
                        ok = False
                        break
                    codes.append(face.code_of[g])
                if ok:
                    jobs.append((len(kept), codes))
                    kept.append(word)
        truth = tex_lists(MF[short], jobs)
        widths = tfm_widths(os.path.join(BUILD, f"trace_{MF[short]}14",
                                        f"{MF[short]}14.tfm"))

        print(f"--- {short} ---")
        # what a browser needs to check the same claim with real text: the width TeX
        # settled on plus the repair the face applies on top, and the padding to take
        # back off a span that has to be measured with spaces around it
        rows = {"space": face.adv(SPACE),
                "space_kerns": sorted([[a, b, v] for (a, b), v in face.kerns.items()
                                       if a == SPACE or b == SPACE])}
        table[short] = {"faces": rows, "words": {}}
        for word, (label, _) in zip(kept, jobs):
            t_codes, t_kerns, t_width = truth[label]
            got = font_list(face, word)
            f_codes = [c for name, _ in got for c in unfold(face, name)]
            f_width = sum(a for _, a in got)
            # what the face costs over the tfm for the very same characters, before
            # any of the program is taken into account: e_overhang's repair only
            drift = sum(face.adv(c) - widths.get(c, 0) for c in f_codes)
            table[short]["words"][word] = {"tex": t_width, "repair": drift,
                                           "expect": t_width + drift,
                                           "kerns": t_kerns, "model": f_width}
            seq_ok = f_codes == t_codes
            w_ok = abs(f_width - (t_width + drift)) <= TOLERANCE
            if not (seq_ok and w_ok):
                bad.append((short, word))
                print(f"   {word!r}")
                print(f"      TeX  {t_codes} kerns={t_kerns} {t_width}")
                print(f"      font {f_codes} {f_width} expect {t_width + drift} "
                      f"(repair {drift:+}) off by {f_width - t_width - drift:+} "
                      f"{'' if seq_ok else 'SEQUENCE'}{'' if w_ok else 'WIDTH'}")
                print(f"           {' '.join(f'{n}({a})' for n, a in got)}")
            else:
                print(f"   {word!r:18} {t_width:6} {len(t_codes)} glyphs "
                      f"{len(t_kerns)} kerns  = TeX{' + repair' if drift else ''}")
    print(f"\n{'ALL WORDS MATCH TEX' if not bad else str(len(bad)) + ' WORDS DIFFER FROM TEX'}")
    for short, word in bad:
        print(f"   {short}: {word!r}")
    if json_out:
        import json
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump(table, fh, ensure_ascii=False, indent=1)
        print(f"wrote {json_out}: "
              + ", ".join(f"{s} {len(v['words'])} words" for s, v in table.items()))
    return 1 if bad else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    out = argv[argv.index("--json") + 1] if "--json" in argv else None
    rest = [a for a in argv if a != "--json" and a != out]
    sys.exit(main(rest or WORDS, out))
