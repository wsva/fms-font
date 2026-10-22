#!/usr/bin/env python3
"""Show TeX's log for one family exactly as 63 will read it."""
import sys

print(open("/tmp/tex_truth/" + sys.argv[1] + ".log", encoding="latin-1").read()[:3000])
print("==== TEX SOURCE ====")
print(open("/tmp/tex_truth/" + sys.argv[1] + ".tex", encoding="latin-1").read()[:600])
