# font/work — the tooling behind the Schulschriften web faces

The faces the app serves (`public/fonts/entenmann-*.woff2`, five German school
scripts × four styles) are built here from the CTAN `schulschriften` METAFONT
sources mirrored in `../metafont-source`. Nothing in this directory is needed at
runtime; it is needed the next time somebody changes a face.

Every script carries its own docstring or header comment saying what it asks.
This file only says what a docstring cannot: which scripts are the pipeline,
which are checks, and which are debris.

The numbers are ids in order of writing, not stages - so the groups below do not
line up with the decades, and a new script takes the next free number wherever
the last one landed.

## Pipeline — the only scripts that write a font

| | |
|---|---|
| `01_download.sh` | fetch and unpack the CTAN package |
| `10_build_all.sh` | `mf` → `.tfm`, `mftrace` → `.pfa`, FontForge → `.ttf` |
| `11_style_woff2.py` | **the one writer of `../faces/`**: RIBBI naming, the `e` overhang repair, the ligature program, `.woff2` |
| `ligparse.py` | read a family's character slots and its `ligtable` program out of the `.mf` |
| `ligatures.py` | that program as OpenType: `Face`, `decorate()`, `emit()`, the GSUB/GPOS build |
| `e_overhang.py` | widen the glyphs whose ink runs past their advance |
| `41_shape.py` | a `.fea` interpreter - HarfBuzz is not on this box, so the audits apply the generated rules themselves |

Rebuild with `python3 11_style_woff2.py ../faces` (WSL: the fontTools that works
is the system Python's), then copy `../faces/*.woff2` into the app's
`public/fonts/` and run `71_suite.sh` - `78_shipped_faces.py` is what catches a
rebuild that never reached the app.

## Checks — run all of them with `71_suite.sh`

`54_fmt`/`55_fmt2` a context lookup a shaper can actually match (format 2 reads
its classes through a Coverage that holds only the inputs) · `56_wordend` the
two-step word-end chain survived the folding · `57_parse_audit` the parser read
every entry the `.mf` writes · `59_join_audit` every pair the tfm changes also
changes in the lookups · `60_wordwidth` whole words cost what TeX's program
costs · `62_slot_audit` no program code lacks a glyph · `63_tex_truth` **TeX
itself is the reference**: 260 words against its own box dump · `66_tfm_widths`
per-slot advance against the tfm · `78_shipped_faces` the shipped copy is the
build and carries space, boundary, `calt`/`liga`, `kern`.

A check that reads a path which does not exist reports nothing and passes. The
suite names the faces for that reason; keep it that way.

## Diagnose — invoked by hand when a check fails

`42_dryrun` · `58_steptok` · `61_why_width` · `64_texdbg` · `65_showlog` ·
`67_per_glyph` · `68_rawbox` · `69_eblock` · `70_kern_junction` ·
`13_metrics`/`14`–`19` ink-overlap profiling · `20_shipped_check` ·
`21_render`/`22_inkrender` (+`23`, `24`, `25`, its own test and debug path) ·
`26_inventory` · `27_slots` · `28_phrase` · `33_map`/`34_parse_debug` ·
`12_verify_faces`.

## Look — the proof is a rendered page, not a metric

`serve.mjs [port] [--root <dir>]` then headless Edge. `43_contact` the five
scripts in one sheet · `72_browser_truth` calt on/off widths in the browser ·
`73_render_proof` sentences and words in all five families ·
`75_latex_pairs` the manual's own Musterblatt title against the web face ·
`76_edge_trigger` whether a zero-width character can open a word for GSUB ·
`77_md_body_edge` the app's real `markdown.css`, block edges fixed and unfixed.

Ground truth to compare against: `../examples_from_latex/*.pdf`,
`../schulschriften.pdf`, and the crops those pages load -
`latex_title_{su,dn,la,sas,va}.png`, `pg2-0[1-4].png`, `latex1-1.png`,
`latex2-01.png`. Delete those and the probes render blank.

## Debris — safe to delete, kept only because nothing here is committed

Screenshots and dumps, all regenerable by the script that made them:
`*.log`, `out_*.txt`, `dom*.html`, `gsub_*.xml`, `la-gsub.ttf`,
`out_features.fea`, `p-0[1-9].png`/`p-1*.png`/`p-2*.png`, `p75_*`, `e76_*`,
`e77_*`, `pairs*`, `render_proof.png`, `rp_*`, `q*.png`, `shot_*`, `i_*`,
`ink_*`, `crop_l*`, `gt_*`, `tex_probe_*`, `tex_words_*`, `muster_titles.png`,
`contact.png`, `p_la_regular.png`, `p_machen.png`, `preview.html`,
`out_browser.html`, `joinprobe.html`, `__pycache__/`, `prev/`, `clean/`.

`50_probe_el2`, `51_el2_lines`, `52_el2_woff2`, `el2/`,
`../la-el2-schulschriften/`: the FontMeme "LA El 2" trial. Rejected - it cannot
join letters the way LaTeX does - and its 1995 shareware licence forbids shipping
a converted copy anyway.

`74_tex_words.py` and `_probe_alpha.sh`, `_probe_dvips.sh`, `_probe_enc.sh`,
`_probe_t1.py`: a **dead end, recorded so nobody walks into it again** - mftrace's
`.pfa` cannot be used as a TeX text font, so TeX cannot be made to set a picture
of a word from these traces. Its `Encoding` and `CharStrings` do not pair up the
way the tfm slots read; FontForge maps glyphs by *name*, which is why the TTF
faces are correct and `dvips` output is garbage. The authentic LaTeX renderings
are `../schulschriften.pdf` (pages 17–21 are the five Musterblätter) and
`../examples_from_latex/`.

`_chk.py`, `_dbg.py`, `_probe.py`, `_probe_feats.py`, `_probe_muster.ps1`,
`_probe_split.ps1`: one-off questions already answered. `_probe_crop.ps1` is
worth keeping - it splits a tall screenshot into bands a human can read, which
every visual check above needs.

## Environment notes, earned the hard way

- **WSL is NAT'd**: a server inside it is not `127.0.0.1` to the Windows browser,
  so `serve.mjs` runs on Windows.
- **Headless Edge needs an absolute `--screenshot=` path** - a relative one fails
  with `Zugriff verweigert (0x5)`.
- **`dvips -u map` resolves through kpathsea, not cwd**: put the run directory on
  `DVIPSHEADERS` with a *leading colon* (`:/tmp/x:/tmp/build//`) or `tex.pro`
  stops being found.
- **`\font` is forbidden inside `\def`**, and `t1binary` (not `t1asm`) converts a
  `.pfa` to `.pfb`.
- PowerShell 5.1 mangles `$(...)`, quotes and here-strings on the way into
  `wsl -e bash -lc`: put real logic in a script file and run that.
- The app's dev server is on **port 30000**, and `font/` is gitignored by the app
  repo because it is a clone of <https://github.com/wsva/fms-font>.
