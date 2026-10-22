#!/usr/bin/env python3
"""Show the raw TeX box dump for one word, as the log wrote it."""
import re
import sys

family, label = sys.argv[1], int(sys.argv[2])
log = open(f"/tmp/tex_truth/{family}.log", encoding="latin-1").read()
i = log.index(f"@{label} ")
print(log[i:i + 700])
