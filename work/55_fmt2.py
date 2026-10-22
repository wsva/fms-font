"""What does the compiled format-2 subtable actually look like in memory?

fontTools merges `sub [ctx] a' by X; ... sub [ctx] z' by Y;` into one chained
SingleSubst whose input is a single 60-glyph class, which it then encodes as
format 2 (class sets) rather than format 3 (coverages). Whether a shaper can
match that depends on which glyphs the Coverage table ended up holding.

Usage: 55_fmt2.py <ttf> [...]
"""
import sys

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot

print("convertFormats on BaseTable:", hasattr(ot.BaseTable, "convertFormats"))


def fmt(st):
    return getattr(st, "format", None) or getattr(st, "Format", None)


def sizes(v):
    if isinstance(v, list):
        return f"list[{len(v)}] of {type(v[0]).__name__}"
    if hasattr(v, "glyphs"):
        return f"{type(v).__name__} {len(v.glyphs)} glyphs"
    return type(v).__name__


for path in sys.argv[1:]:
    print("#" * 70)
    print(path)
    gsub = TTFont(path)["GSUB"].table
    for i, lk in enumerate(gsub.LookupList.Lookup):
        if lk.LookupType != 6:
            continue
        head = ", ".join(f"{type(s).__name__}#{fmt(s)}" for s in lk.SubTable[:3])
        print(f"  lookup {i}: {len(lk.SubTable)} subtables -> {head}")
        two = [j for j, st in enumerate(lk.SubTable) if fmt(st) == 2]
        if not two:
            continue
        st = lk.SubTable[two[0]]
        print(f"   !! format 2 at subtable {two[0]}; attributes:")
        for attr in sorted(vars(st)):
            v = getattr(st, attr)
            if v is None or isinstance(v, int):
                print(f"        {attr:24} {v}")
            else:
                print(f"        {attr:24} {sizes(v)}")
        cov = getattr(st, "Coverage", None)
        if cov is not None and hasattr(cov, "glyphs"):
            print("        Coverage:", " ".join(cov.glyphs[:8]), "...")
        bcd = getattr(st, "BacktrackClassDef", None)
        if bcd is not None:
            gs = sorted(getattr(bcd, "glyphs", {}) or {})
            print(f"        BacktrackClassDef glyphs ({len(gs)}):", " ".join(gs[:8]), "...")
            print("        are they in Coverage?",
                  all(g in set(cov.glyphs) for g in gs) if cov else "?")
        break
