#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Give a converted Schulschriften face back its ligature program.

The METAFONT sources cut two or three forms of nearly every letter plus a handful
of connector strokes, and the tfm's ligature/kern program chooses between them as
TeX sets a word. mftrace carried the glyphs over - all 185 of them, sitting under
tex256 names like "aogonek" and "hungarumlaut" - but nothing carried the program.
So the web faces draw every letter in its isolated form: no joins, and an "e"
whose exit stroke is simply overwritten by whatever comes next.

This reads the program out of the sources and expresses it as OpenType lookups,
which is the one place a browser will run it for free:

  * A positional form ("a" before "e" becomes a's Endform) is a contextual single
    substitution - one glyph for one glyph, so a letter can still be re-examined
    against its other neighbour afterwards.
  * An inserted connector cannot be expressed directly: GSUB substitutes, it does
    not insert. So the connector is folded into the glyph on its left as a
    TrueType composite with the summed advance, which is exactly the position and
    width TeX would have given it.
  * The lookups run in the order TeX would have reached each decision: true
    ligatures, word-start forms, right forms, left forms, word-start connectors.
    All of them but the ligatures go in one `calt` lookup list, because a shaper
    picks the order features run in and that order is not ours to choose.

Usage: ligatures.py <in.ttf> <out.ttf> <family> [-n]   (-n: report, write no font)
"""
import os
import re
import sys

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ligparse import START, char_codes, count_entries, enc_names, kern_values, parse_lig

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "metafont-source")
SPACE = 32                                    # the tfm's boundarychar

#: A block edge has no glyph in front of the first word, so GSUB cannot open it and
#: the word loses the entry stroke TeX gives it from the boundarychar. The faces
#: therefore also answer to a zero-width trigger there, which the page puts at the
#: edges of a text block as generated content - not in the DOM, so it is not copied,
#: not searched and not spoken. U+2060 would have been the semantic match but it is
#: default-ignorable, and a shaper drops those before GSUB ever sees them.
BOUNDARY = 0x200B
BOUND_NAME = "boundary"

#: the faces' file short name -> the METAFONT family whose sources hold the program
MF = {"su": "wesu", "dn": "wedn", "la": "wela", "sas": "wesa", "va": "weva"}


class Face:
    """One converted face, plus the code <-> glyph-name correspondence.

    Takes a path or an already-open TTFont - 11_style_woff2.py decorates the face
    it is already holding, so the program is applied in the same pass that writes
    the binaries and cannot be skipped on a rebuild.
    """

    def __init__(self, path, family):
        root = os.path.join(SRC, family)
        self.family = family
        self.codes = char_codes(root)                     # code -> width in ut#
        self.name_of = dict(enc_names())                  # code -> tex256 glyph name
        lig = os.path.join(root, f"{family}14_lig.mf")
        self.rules = parse_lig(lig)
        # a program the parser only read part of still compiles and still ships, and
        # the missing rules are exactly the ones that make a word look like a word
        want = sum(count_entries(lig).values())
        if want != len(self.rules):
            raise SystemExit(f"{family}: {lig} writes {want} ligtable entries but "
                             f"parse_lig read {len(self.rules)} - rules would be "
                             f"lost from the face")
        self.kvars = kern_values(root, f"{family}14")
        self.ttf = path if hasattr(path, "save") else TTFont(path)
        self.glyf, self.hmtx = self.ttf["glyf"], self.ttf["hmtx"]
        self.scale = self.hmtx["A"][0] / self.codes[ord("A")]
        # The program's kerns, in face units and keyed by the pair of *codes* TeX
        # has at the junction - which is the settled form, not the typed letter.
        # emit() needs them as glyph-name pairs and glyph_for() as the gap inside a
        # composite, and both are guesses about the future unless they are read off
        # the program once here. `||` heads are the boundarychar, and these fonts set
        # it to oct"040', so a word-start kern is a kern after the space glyph.
        self.kerns = {}
        for r in self.rules:
            if r.action != "kern":
                continue
            ut = self.kvars[r.result] if isinstance(r.result, str) else r.result
            value = round(self.scale * ut)
            for head in {SPACE if h == START else h for h in r.first}:
                self.kerns[(head, r.second)] = self.kerns.get((head, r.second), 0) + value
        in_font = set(self.ttf.getGlyphOrder())
        reachable = set(self.ttf.getBestCmap().values())
        self.missing = [c for c in self.codes if self.name_of[c] not in in_font]
        self.typed = sorted(c for c in self.codes
                            if self.name_of[c] in reachable)
        self.parts_of = {}                                # composite name -> codes
        self.composites = {}                              # codes -> composite name
        self.fea = None                                   # set by decorate()

    def adv(self, code):
        return self.hmtx[self.name_of[code]][0]

    def _adopt(self, name, glyph, advance):
        """Add a drawn glyph: assigning into glyf appends it to the glyph order,
        which is the one list every other table then has to agree with."""
        self.glyf[name] = glyph
        self.hmtx.metrics[name] = (advance, 0)
        self.ttf.setGlyphOrder(self.glyf.glyphOrder)

    def add_space(self):
        """The faces have no U+0020, so a word boundary is invisible to GSUB.

        Registering the code has to happen every time, not only when the glyph is
        missing: a face rebuilt from an already-decorated file arrives here with a
        space, and skipping the enumeration step drops every letter+space pair -
        which is precisely the set that produces the word-end forms.
        """
        if "space" not in self.glyf.keys():
            quad = _fontdimen(self.family, "font_quad")
            width = round(1000 * _fontdimen(self.family, "font_normal_space") / quad)
            g = Glyph()
            g.numberOfContours = 0
            g.xMin = g.yMin = g.xMax = g.yMax = 0
            self._adopt("space", g, width)
            self.ttf["cmap"].tables[-1].cmap[SPACE] = "space"
        self.name_of[SPACE] = "space"
        if SPACE not in self.typed:
            self.typed.append(SPACE)
            self.typed.sort()

    def add_boundary(self):
        """The zero-width stand-in for the boundarychar, drawn as nothing.

        It is deliberately not one of the program's codes: it only ever appears as
        context, never as a letter a rule rewrites, so it stays out of `codes`,
        `typed` and the kern table, and no `pos` is written against it.
        """
        if BOUND_NAME not in self.glyf.keys():
            g = Glyph()
            g.numberOfContours = 0
            g.xMin = g.yMin = g.xMax = g.yMax = 0
            self._adopt(BOUND_NAME, g, 0)
        self.ttf["cmap"].tables[-1].cmap[BOUNDARY] = BOUND_NAME

    def glyph_for(self, codes):
        """Name of the glyph that lays `codes` out end to end.

        A connector TeX inserted next to a letter sits at a junction the program has
        already kerned, and once the two are one glyph that junction is interior: no
        GPOS pair can ever reach it again. So the kern is baked into the component
        placement and the advance here, which is where TeX put it too.
        """
        codes = tuple(codes)
        if len(codes) == 1:
            return self.name_of[codes[0]]
        if codes in self.composites:
            return self.composites[codes]
        name = "p" + "_".join(f"{c:03o}" for c in codes)
        pen = TTGlyphPen(self.ttf.getGlyphSet())
        x = 0
        for i, code in enumerate(codes):
            if i:
                x += self.kerns.get((codes[i - 1], code), 0)
            pen.addComponent(self.name_of[code], (1, 0, 0, 1, x, 0))
            x += self.adv(code)
        self._adopt(name, pen.glyph(), x)
        self.composites[codes] = name
        self.parts_of[name] = list(codes)
        return name


def _fontdimen(family, key):
    text = open(os.path.join(SRC, family, f"{family}14.mf"), encoding="latin-1").read()
    m = re.search(rf"{key}\s*(?::=|=)?\s*([\d.]+)\s*pt#", text)
    if not m:
        raise KeyError(f"{family}: {key} not found in the driver")
    return float(m.group(1))


# ---------------------------------------------------------------- TeX's program
def resolve(lst, index, limit=60):
    """Apply the ligature program to a glyph list until nothing further matches.

    TeX walks the list with pushback; restarting the scan after every step reaches
    the same fixed point without having to model which glyph gets pushed back.
    """
    lst = list(lst)
    for _ in range(limit):
        for i in range(len(lst) - 1):
            for r in index.get((lst[i], lst[i + 1]), ()):
                keep_l, keep_r = r.action
                if not keep_l and not keep_r:
                    lst[i:i + 2] = [r.result]
                elif not keep_l:
                    lst[i] = r.result
                elif not keep_r:
                    lst[i + 1] = r.result
                else:
                    lst[i + 1:i + 1] = [r.result]
                break
            else:
                continue
            break
        else:
            return lst
    raise RuntimeError(f"{' '.join(f'{c:03o}' for c in lst)} does not settle")


def analyse(face):
    """Work out, for every pair a word can contain, what the program makes of it.

    Returns (right_forms, left_forms, ligatures): the first maps a pair to the
    glyph that replaces its right member, the second groups left-hand outputs by
    the context that produces them, the third holds the true two-to-one ligatures.
    """
    index = {}
    for r in face.rules:
        if r.action == "kern" or r.word_start:
            continue
        for head in r.first:
            index.setdefault((head, r.second), []).append(r)
    ambiguous = {k: v for k, v in index.items() if len(v) > 1}

    order = set(face.ttf.getGlyphOrder())
    alphabet = [c for c in sorted(face.codes) if c in face.name_of
                and face.name_of[c] in order] + [SPACE]
    rights = face.typed

    right_forms, left_forms, ligatures = {}, {}, {}
    for x in alphabet:
        for y in rights:
            res = resolve([x, y], index)
            if res == [x, y]:
                continue
            if len(res) == 1:
                ligatures[(x, y)] = res[0]
                continue
            head, tail = res[:-1], res[-1]
            if tail != y:
                right_forms.setdefault(x, {})[y] = tail
            if head != [x]:
                left_forms.setdefault((x, tuple(head)), set()).add(tail)
    return alphabet, right_forms, left_forms, ligatures, ambiguous


def word_start(face):
    """The `||:` rules, split into the forms that replace the letter and the
    connectors that only precede it - the first has to run before the pair rules
    so the letter's new identity is what they see, the second after, so a
    word-initial letter keeps whatever connector its own follower earned it.

    Each value is [boundary glyphs, result code]: what can open a word before the
    letter, and what the rule does at that point.
    """
    replace, insert = {}, {}
    for r in face.rules:
        if not r.word_start or r.action == "kern":
            continue
        keep_l, keep_r = r.action
        if not keep_l:
            continue                      # a word can't be replaced away
        bucket = replace if not keep_r else insert
        bucket.setdefault(r.second, [{c for c in r.first if c != START}, r.result])[0] \
            |= {c for c in r.first if c != START}
    return replace, insert


def decorate(face, verbose=True, label=""):
    """Work out the program, build the composites and bolt the lookups on the face.

    Returns the .fea text, which is worth keeping: it is the program translated
    into the one form a browser will run.
    """
    face.add_space()
    face.add_boundary()
    alphabet, right_forms, left_forms, ligatures, ambiguous = analyse(face)
    wr_start, wi_start = word_start(face)

    # METAFONT ends a word by inserting a marker before the space and handing the
    # letter its Endform, so the whole word-end vocabulary comes out of the
    # letter+space pairs. Losing those pairs costs a word-final exit stroke on
    # every word and shows up in no metric of the build - so it fails here.
    if not any(SPACE in contexts for contexts in left_forms.values()):
        raise SystemExit(f"{label}: the program has no word-end forms - the "
                         f"letter+space pairs were not enumerated")

    # A word-initial letter can itself have taken a connector from its follower,
    # so the entry stroke is offered to every shape it may already have become.
    # What may precede it is what the word-start rule named - the boundary, never
    # the letters that follow: those are already settled inside the shape, and
    # putting them in the prefix lets the entry stroke fire in the middle of a word.
    entry = {}
    for letter, (boundaries, connector) in wi_start.items():
        forms = {letter} | {head[0] for (x, head) in left_forms
                            if x == letter and len(head) == 1}
        for form in forms:
            entry.setdefault((connector, form), set()).update(boundaries)
        for (x, head) in left_forms:
            if x == letter and len(head) > 1:
                entry.setdefault((connector,) + tuple(head), set()).update(boundaries)

    fea = emit(face, right_forms, left_forms, ligatures, entry, wr_start)
    face.fea = fea
    if verbose:
        ends = sum(1 for contexts in left_forms.values() if SPACE in contexts)
        print(f"{label}: {len(alphabet)} glyphs in play, {len(ligatures)} ligatures, "
              f"{len(wr_start) + len(wi_start)} word-start, "
              f"{len(right_forms)} right-form, {len(left_forms)} left-form "
              f"({ends} word-end) rules, "
              f"{len(face.composites)} composites, {len(ambiguous)} ambiguous pairs")
    addOpenTypeFeaturesFromString(face.ttf, fea, filename=f"{face.family}.fea")
    check_compiled(face.ttf, label or face.family)
    _fix_post(face)
    return fea


def check_compiled(font, label=""):
    """Refuse a compiled context lookup that no shaper can match.

    A class-based (format 2) context subtable reads a glyph's class out of its
    Coverage table, and feaLib puts only the input letters there - so a rule whose
    context is a glyph class resolves the context to class 0 and never fires. It
    compiles clean and costs nothing to leave in, which is exactly why the build
    has to fail on it rather than wait for someone to notice the joins are missing.
    """
    dead = []
    for tag in ("GSUB", "GPOS"):
        table = font.get(tag)
        if table is None:
            continue
        for i, lk in enumerate(table.table.LookupList.Lookup):
            if lk.LookupType not in (5, 6):
                continue
            for j, st in enumerate(lk.SubTable):
                if getattr(st, "Format", None) == 2 or getattr(st, "format", None) == 2:
                    dead.append(f"{tag} lookup {i} subtable {j}")
    if dead:
        raise SystemExit(f"{label}: class-based context subtables, dead in a "
                         f"shaper: {', '.join(dead)}")


def build(path, out, family, verbose=True, save=True):
    face = Face(path, family)
    fea = decorate(face, verbose, os.path.basename(path))
    open(os.path.join(HERE, "out_features.fea"), "w", encoding="utf-8").write(fea)
    if save:
        face.ttf.save(out)
        if verbose and face.missing:
            print("  codes the face has no glyph for:",
                  ", ".join(f"{c:03o}" for c in face.missing))
    return face


def _fix_post(face):
    """post format 2 lists names by index, so new glyphs have to be announced."""
    post = face.ttf.get("post")
    if post is None or getattr(post, "formatType", 2) != 2:
        return
    order = face.ttf.getGlyphOrder()
    post.glyphOrder = list(order)
    post.map = {n: i for i, n in enumerate(order)}
    post.extraNames = []


def _cls(names):
    return names[0] if len(names) == 1 else "[" + " ".join(sorted(names)) + "]"


def emit(face, right_forms, left_forms, ligatures, entry, wr_start):
    n = face.name_of

    # A context that names the boundarychar also accepts the zero-width trigger:
    # both mean "there is no letter on this side", which is all the rule asks.
    # As an *input* the trigger would be a letter, and it is not, so this is used
    # for contexts only.
    def ctx_of(codes):
        names = {n[c] for c in codes}
        if SPACE in codes:
            names.add(BOUND_NAME)
        return _cls(sorted(names))

    L = ["languagesystem DFLT dflt;", "languagesystem latn dflt;", "",
         "# Generated by ligatures.py from the family's *_lig.mf - do not edit."]
    lookups = []

    if ligatures:
        L.append("lookup Ligatures {")
        for (x, y), res in sorted(ligatures.items()):
            L.append(f"  sub {n[x]} {n[y]} by {n[res]};")
        L.append("} Ligatures;\n")
        lookups.append("Ligatures")

    if wr_start:
        L.append("lookup WordForms {")
        for letter, (boundaries, result) in sorted(wr_start.items()):
            ctx = ctx_of(boundaries | {SPACE})
            L.append(f"  sub {ctx} {n[letter]}' by {n[result]};")
        L.append("} WordForms;\n")
        lookups.append("WordForms")

    if right_forms:
        # `|=: ` pairs: the left letter is only the context, the right one changes.
        L.append("lookup RightForms {")
        for x, per_right in sorted(right_forms.items()):
            groups = {}
            for y, tail in per_right.items():
                groups.setdefault(tail, set()).add(y)
            for tail, ys in sorted(groups.items()):
                L.append(f"  sub {n[x]} {_cls([n[y] for y in ys])}' by {n[tail]};")
        L.append("} RightForms;\n")
        lookups.append("RightForms")

    if left_forms:
        L.append("lookup LeftForms {")
        for (x, head), contexts in sorted(left_forms.items()):
            L.append(f"  sub {n[x]}' {ctx_of(contexts)} "
                     f"by {face.glyph_for(head)};")
        L.append("} LeftForms;\n")
        lookups.append("LeftForms")

    if entry:
        # One lookup per rule. feaLib merges rules that share a context into a
        # single class-based (format 2) subtable, and in GSUB format 2 a glyph's
        # class is read from a Coverage table that holds only the input letters:
        # the context glyphs land in class 0, so the rule can never match and the
        # whole lookup is dead weight that only shows up when a face is rendered.
        # Separate lookups stay coverage-based, which every shaper can match.
        for i, (parts, contexts) in enumerate(sorted(entry.items())):
            ctx = ctx_of(contexts | {SPACE})
            L.append(f"lookup WordJoins{i:02d} {{")
            L.append(f"  sub {ctx} {face.glyph_for(parts[1:])}' "
                     f"by {face.glyph_for(parts)};")
            L.append(f"}} WordJoins{i:02d};\n")
        lookups += [f"WordJoins{i:02d}" for i in range(len(entry))]

    # The two-to-one ligatures belong to `liga` by meaning, but a shaper picks the
    # order features run in and that order is not ours to choose, so they are also
    # the first lookup of `calt`: whichever feature reaches them first converts
    # them, and the second pass finds nothing left to do.
    L.append("feature liga {")
    if ligatures:
        L.append("  lookup Ligatures;")
    L.append("} liga;\n")
    L.append("feature calt {")
    for name in lookups:
        L.append(f"  lookup {name};")
    L.append("} calt;\n")

    if face.kerns:
        # A kern survives the trip to GPOS only under the names the two glyphs have
        # when the shaper is done with them. The program may have given either side
        # another form, and may have had a connector folded into it as a composite -
        # so `pos a b` has to be written for the letter, for the composites that now
        # carry it, and for every combination of the two. A junction that ended up
        # *inside* a composite is not here: glyph_for baked that one into its width.
        starts, ends = {}, {}
        for name, parts in face.parts_of.items():
            starts.setdefault(parts[0], set()).add(name)
            ends.setdefault(parts[-1], set()).add(name)
        L.append("feature kern {")
        for (a, b), value in sorted(face.kerns.items()):
            lefts = ({n[a]} | ends.get(a, set())) if a in n else set(ends.get(a, set()))
            rights = ({n[b]} | starts.get(b, set())) if b in n else set(starts.get(b, set()))
            for x in sorted(lefts):
                for y in sorted(rights):
                    L.append(f"  pos {x} {y} {value};")
        L.append("} kern;")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3], save="-n" not in sys.argv)
