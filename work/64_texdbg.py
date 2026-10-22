#!/usr/bin/env python3
"""What did TeX actually write? Run one box dump and show the log."""
import os
import subprocess

WORK = "/tmp/tex_truth"
os.makedirs(WORK, exist_ok=True)
tex = os.path.join(WORK, "su.tex")
with open(tex, "w") as fh:
    fh.write("\\showboxdepth=100 \\showboxbreadth=5000\n")
    fh.write("{\\font\\f=wesu14 at 14.0pt \\f \\setbox0=\\hbox{\\char128\\char83}"
             "\\message{@0 \\the\\wd0}\\showbox0}\n")
env = dict(os.environ, TFMFONTS=":/tmp/build/trace_wesu14//", TEXINPUTS=":")
r = subprocess.run(["tex", "-interaction=batchmode", "su.tex"], cwd=WORK, env=env,
                   capture_output=True, text=True)
print("rc", r.returncode, "out|", r.stdout, "err|", r.stderr)
print(os.listdir(WORK))
log = os.path.join(WORK, "su.log")
if os.path.exists(log):
    print(open(log, encoding="latin-1").read()[:2000])
