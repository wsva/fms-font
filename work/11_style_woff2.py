#!/usr/bin/env python3
"""Post-process the generated TTFs: set RIBBI (regular/italic/bold/bold-italic)
OS/2 fsSelection bits, usWeightClass, and name-table family/subfamily, keep
head/post italicAngle at 0 (the 'italic' faces are already geometrically slanted
by the METAFONT `slant` transform), then write WOFF2 alongside each TTF.

Also repairs the `e` advance overhang (see e_overhang.py) and gives every face
back the ligature/kern program its tfm carried (see ligatures.py) - this script
is the one place faces are written, so neither can be forgotten on a rebuild.

Usage: 11_style_woff2.py <faces_dir> [--only slug-substring]...
"""
import sys, os, glob
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e_overhang import repair_overhang
from ligatures import MF, Face, decorate

FAMILY = {
    "su":  "Suetterlinschrift Entenmann",
    "dn":  "Deutsche Normalschrift Entenmann",
    "la":  "Lateinische Ausgangsschrift Entenmann",
    "sas": "Schulausgangsschrift Entenmann",
    "va":  "Vereinfachte Ausgangsschrift Entenmann",
}
# ftag -> (subfamily, bold, italic, weight_class)
STYLE = {
    "regular":      ("Regular",     0, 0, 400),
    "bold":         ("Bold",        1, 0, 700),
    "italic":       ("Italic",      0, 1, 400),
    "bold-italic":  ("Bold Italic", 1, 1, 700),
}

FS_ITALIC, FS_BOLD, FS_REGULAR = 1 << 0, 1 << 5, 1 << 6

#: where the generated .fea files of this run are written, for review
FEAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "features")
os.makedirs(FEAS, exist_ok=True)


def set_name(f, nameID, s):
    f["name"].setName(s, nameID, 3, 1, 0x409)   # Windows
    f["name"].setName(s, nameID, 1, 0, 0)        # Macintosh


def main(out_dir, only=()):
    count = 0
    for ttf in sorted(glob.glob(os.path.join(out_dir, "entenmann-*.ttf"))):
        base = os.path.basename(ttf)[:-4]                 # entenmann-<short>-<ftag>
        if only and not any(o in base for o in only):
            continue
        parts = base.split("-")
        short, ftag = parts[1], "-".join(parts[2:])
        if short not in FAMILY or ftag not in STYLE:
            print(f"skip (unknown) {base}")
            continue
        fam = FAMILY[short]
        sub, bold, italic, wc = STYLE[ftag]
        f = TTFont(ttf)
        os2 = f["OS/2"]
        fs = os2.fsSelection & ~(FS_ITALIC | FS_BOLD | FS_REGULAR)
        if bold:
            fs |= FS_BOLD
        if italic:
            fs |= FS_ITALIC
        if not bold and not italic:
            fs |= FS_REGULAR
        os2.fsSelection = fs
        os2.usWeightClass = wc
        # head.macStyle: bit0 Bold(1), bit1 Italic(2) -- keep in sync with fsSelection
        mac = f["head"].macStyle & ~((1 << 0) | (1 << 1))
        if bold:
            mac |= 1 << 0
        if italic:
            mac |= 1 << 1
        f["head"].macStyle = mac
        # name table: RIBBI grouping
        psname = f["name"].getName(6, 3, 1, 0x409)
        psname = str(psname) if psname else f"Entenmann{short.upper()}-{sub.replace(' ','')}"
        full = f"{fam} {sub}" if sub != "Regular" else fam
        set_name(f, 1, fam)
        set_name(f, 2, sub)
        set_name(f, 4, full)
        set_name(f, 6, psname)
        set_name(f, 16, fam)
        set_name(f, 17, sub)
        # glyphs already slanted by METAFONT; do not let engines add synthetic slant
        if "post" in f:
            f["post"].italicAngle = 0.0
        repair_overhang(f, base)
        # A face this script has already decorated still carries last run's
        # lookups, so drop them and let the current generator have the last word:
        # skipping a face that "already has GSUB" silently ships an old program.
        # (A lazily opened font only lists the tables it has read, so the reader
        # has to be cleared too, or the table loads back on first touch.)
        for tag in ("GSUB", "GPOS"):
            f.reader.tables.pop(tag, None)
            f.tables.pop(tag, None)
        face = Face(f, MF[short])
        # the rule counts belong in the build log: a program that lost its word-end
        # or word-join rules is invisible in every other metric of the face
        decorate(face, verbose=True, label=base)
        # the translated program is worth keeping next to the binary it made
        with open(os.path.join(FEAS, base + ".fea"), "w", encoding="utf-8") as fh:
            fh.write(face.fea)
        f.save(ttf)
        g = TTFont(ttf)
        g.flavor = "woff2"
        g.save(ttf[:-4] + ".woff2")
        count += 1
        print(f"  {base}: fam='{fam}' sub='{sub}' fs=0b{bin(fs)} wc={wc}")
    print(f"post-processed {count} faces -> ttf+woff2")


if __name__ == "__main__":
    argv = sys.argv[1:]
    only = argv[argv.index("--only") + 1:] if "--only" in argv else ()
    main(argv[0], only)
