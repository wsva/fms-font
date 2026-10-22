#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read a Schulschriften METAFONT font: its character slots and its ligature program.

The web conversion is missing exactly one thing - the tfm ligature/kern program -
so before that can be turned into OpenType lookups, the program has to be read
out of the sources. Two pieces of information are needed:

  * which glyph sits at which character code. mftrace named the slots from
    tex256.enc, so the word-final form of "a" (oct 241) is called "aogonek" and
    the connectors live in the control-code slots under accent names. The codes
    come from the beginchar lines, the names from the encoding vector.
  * the ligtable statements themselves. METAFONT writes them into the tfm as a
    program over adjacent glyph pairs, with four forms:

      =:     both glyphs are replaced by the result     (a true ligature)
      =:|    the left glyph is replaced, the right kept (a positional form)
      |=:    the right glyph is replaced, the left kept
      |=:|   neither is replaced, the result is inserted between them
      kern v the pair is moved together by the value v

    "||" stands for the beginning of the input, so a ligtable headed
    "|| : space : ( : ..." is a word-start rule.

  * a long head list can be followed by a *step label* (`1::`) and end in
    `skipto 1` instead of `;`. That is program structure, not more pairs: every
    pattern in the table is tested against every head character, so the labels
    and the jump are read and dropped. weva uses this form, and a parser that
    stops at the label loses its word-initial connector rules along with its
    kerning.

Usage: as a module - see 40_build_gsub.py
"""
import os
import re

ENC_PATH = "/usr/share/texlive/texmf-dist/fonts/enc/dvips/base/tex256.enc"

BEGIN = re.compile(r'beginchar\(\s*(oct"[0-7]+"|"(?:\\.|[^"\\])*")\s*,\s*([^,)]+)')
TOKEN = re.compile(r'''
    (?P<oct>oct"[0-7]+")
  | (?P<char>"(?:\\.|[^"\\])*")
  | (?P<num>-?\d+(?:\.\d+)?ut\#)
  | (?P<label>\d+)
  | (?P<act>\|?=:?\|?)
  | (?P<null>\|\|)
  | (?P<colon>:)
  | (?P<comma>,)
  | (?P<semi>;)
  | (?P<word>[A-Za-z][A-Za-z0-9_#]*)
''', re.X)

#: ligature code -> (keep_left, keep_right)
ACTIONS = {"=:": (False, False), "=:|": (False, True),
           "|=:": (True, False), "|=:|": (True, True)}

#: METAFONT's "||" - the beginning of the input, i.e. word start
START = -1

#: the ligature actions, longest first: each is a substring of the next-widest one
LIG_OPS = ("|=:|", "=:|", "|=:", "=:")


def count_entries(path):
    """{action: how many entries the source writes}, counted off the text itself.

    The parser has to reproduce this exactly. Reading a ligtable that ends in a
    step label as if it stopped at the head list loses rules without any error -
    the font just quietly stops joining words - so the count is what the build
    checks the parsed rule list against.
    """
    text = re.sub(r"%[^\n]*", "", open(path, encoding="latin-1").read())
    out = {op: len(re.findall(r"(?<![|=:])" + re.escape(op) + r"(?![|])", text))
           for op in LIG_OPS}
    # `kern` needs word boundaries of its own: the kern variables are skern#, Bkern#
    out["kern"] = len(re.findall(r"(?<![A-Za-z0-9_#])kern(?![A-Za-z0-9_#])", text))
    return out


def _kern_value(tok):
    """'-20ut#' -> -20.0; a bare name is a variable the caller looks up."""
    return float(tok[:-3]) if tok.endswith("ut#") else tok


def enc_names(path=ENC_PATH):
    """tex256.enc -> {slot: glyph name}; the array is positional."""
    text = open(path, encoding="latin-1").read()
    body = text[text.index("[") + 1:text.rindex("]")]
    names = re.sub(r"%[^\n]*", "", body).split()
    assert len(names) == 256, f"{path}: {len(names)} entries, expected 256"
    return {i: n.lstrip("/") for i, n in enumerate(names)}


def _code(tok):
    if tok.startswith('oct"'):
        return int(tok[4:-1], 8)
    return ord(tok[1])


def char_codes(family_dir):
    """{code: width_in_font_units_source} for one family, read from beginchar."""
    out = {}
    for fn in sorted(os.listdir(family_dir)):
        if not fn.endswith(("_gr.mf", "_kl.mf", "_sz.mf")):
            continue
        for line in open(os.path.join(family_dir, fn), encoding="latin-1"):
            m = BEGIN.search(line)
            if m:
                w = re.match(r"([\d.]+)", m.group(2))
                out[_code(m.group(1))] = float(w.group(1)) if w else None
    return out


def kern_values(family_dir, prefix):
    """{"Bkern#": -10.5, ...} in ut#, from the family's _def.mf."""
    path = os.path.join(family_dir, f"{prefix}_def.mf")
    text = re.sub(r"%[^\n]*", "", open(path, encoding="latin-1").read())
    return {m.group(1): float(m.group(2))
            for m in re.finditer(r"(\w+#)\s*:=\s*(-?[\d.]+)\s*ut#", text)}


class Rule:
    """One ligtable entry: any of `first` followed by `second` triggers `action`.

    START (-1) in `first` is METAFONT's "||", the beginning of the input; the
    rest of that head list are the characters that can also stand at a word
    boundary, so a rule carrying START is a word-start rule.
    """

    def __init__(self, first, second, action, result):
        self.first = first            # set of codes, possibly containing START
        self.second = second
        self.action = action          # (keep_left, keep_right) or "kern"
        self.result = result          # code, or a kern variable name

    @property
    def word_start(self):
        return START in self.first

    def applies(self, left, right):
        return right == self.second and left in self.first

    def __repr__(self):
        head = ",".join("||" if c == START else f"{c:03o}" for c in sorted(self.first))
        act = self.action if isinstance(self.action, str) else (
            ("|" if self.action[0] else "") + "=:" + ("|" if self.action[1] else ""))
        res = f"{self.result:g}" if isinstance(self.result, float) else (
            self.result if isinstance(self.result, str) else f"{self.result:03o}")
        return f"ligtable {head}: {self.second:03o} {act} {res}"


def parse_lig(path):
    """The whole ligature program of one family as a flat rule list."""
    text = re.sub(r"%[^\n]*", "", open(path, encoding="latin-1").read())
    toks = [(m.lastgroup, m.group()) for m in TOKEN.finditer(text)]
    rules, i = [], 0
    while i < len(toks):
        kind, val = toks[i]
        if kind != "word" or val != "ligtable":
            i += 1
            continue
        i += 1
        head, second = None, None
        while i < len(toks):
            if toks[i][0] == "word" and toks[i][1] == "skipto":
                i += 2               # `skipto n` ends the chain, the table follows
                continue
            if toks[i][0] == "label" and i + 1 < len(toks) and toks[i + 1][0] == "colon":
                i += 1               # a step label is not a character
                while i < len(toks) and toks[i][0] == "colon":
                    i += 1
            # a ':'-separated run of characters: all but the last are the head
            run = []
            while i < len(toks) and toks[i][0] in ("char", "oct", "null"):
                run.append(toks[i][1])
                i += 1
                if i < len(toks) and toks[i][0] == "colon":
                    i += 1
                else:
                    break
            if not run:
                break
            if i < len(toks) and toks[i][0] == "label":
                # the run ran into a step label, so it was the whole head list and
                # the first pattern only comes after the label
                head = sorted(set(head or ()) |
                              {START if r == "||" else _code(r) for r in run})
                continue
            if head is None:
                head = [START if r == "||" else _code(r) for r in run[:-1]]
            second = _code(run[-1])
            if i >= len(toks) or toks[i][0] not in ("act", "word"):
                break
            if toks[i][1] == "kern":
                i += 1
                # either a variable defined in the _def file or a literal ut#
                rules.append(Rule(set(head), second, "kern",
                                  _kern_value(toks[i][1])))
                i += 1
            else:
                action = ACTIONS[toks[i][1]]
                i += 1
                result = _code(toks[i][1])
                i += 1
                rules.append(Rule(set(head), second, action, result))
            if i >= len(toks):
                break
            if toks[i][0] == "semi":
                i += 1
                break
            if toks[i][0] == "comma":
                i += 1          # the ligtable's head stays in force for the next item
                continue
            break
    return rules


if __name__ == "__main__":
    import sys
    fam = sys.argv[1] if len(sys.argv) > 1 else "wela"
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "metafont-source", fam)
    drv = fam + "14"
    codes = char_codes(root)
    names = enc_names()
    rules = parse_lig(os.path.join(root, f"{drv}_lig.mf"))
    print(f"{fam}: {len(codes)} chars, {len(rules)} ligtable entries")
    by_action = {}
    for r in rules:
        key = r.action if isinstance(r.action, str) else str(r.action)
        by_action[key] = by_action.get(key, 0) + 1
    print("  by action:", by_action)
    print("  word-start rules:", sum(1 for r in rules if r.word_start))
    # Every code the program mentions has to be a character the font defines,
    # otherwise the conversion lost it and no lookup can be built for the rule.
    bad = set()
    for r in rules:
        for c in set(r.first) | {r.second}:
            if c != START and c not in codes:
                bad.add(("ctx", c))
        if r.action != "kern" and not isinstance(r.result, str) and r.result not in codes:
            bad.add(("result", r.result))
        if isinstance(r.result, str) and r.result not in kern_values(root, drv):
            bad.add(("kernvar", r.result))
    print("  unknown codes:", sorted(bad) or "none")
    if "-v" in sys.argv:
        for r in rules:
            print("   ", r)
