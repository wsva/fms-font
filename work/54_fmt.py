"""Which compiled lookups came out as format 2, and can they be rewritten?

format 2 chain-context subtables index their class sets through a single Coverage
table, so a context glyph that is not in that Coverage can never match its class.
That is the difference between a rule a shaper runs and a rule it skips.
"""
import os
import sys

import fontTools
from fontTools.ttLib import TTFont

print("fontTools", fontTools.version, os.path.dirname(fontTools.__file__))

FACES = sys.argv[1:] or ["faces/entenmann-%s-regular.ttf" % f for f in
                         ("su", "dn", "la", "sas", "va")]
for path in FACES:
    f = TTFont(path)
    gsub = f["GSUB"].table
    print("=" * 70)
    print(os.path.basename(path))
    # which lookup does calt name, and in what order
    for rec in gsub.FeatureList.FeatureRecord:
        if rec.FeatureTag != "calt":
            continue
        idx = rec.Feature.LookupListIndex
        names = []
        for i in idx:
            lk = gsub.LookupList.Lookup[i]
            names.append(f"{i}:{lk.LookupType}")
        print("  calt ->", " ".join(names))
    for i, lk in enumerate(gsub.LookupList.Lookup):
        fmts = [getattr(st, "format", "?") for st in lk.SubTable]
        bad = sum(1 for x in fmts if x == 2)
        kinds = {}
        for st in lk.SubTable:
            k = type(st).__name__
            kinds[k] = kinds.get(k, 0) + 1
        print(f"  lookup {i:2} type={lk.LookupType} subtables={len(fmts):3} "
              f"formats={sorted(set(fmts))} {'<< FORMAT 2: ' + str(bad) if bad else ''} "
              f"{kinds}")
