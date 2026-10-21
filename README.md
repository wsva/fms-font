# font/ — Schulschriften web fonts (converted from CTAN `schulschriften`)

Web-ready TTF + WOFF2 conversions of the five German school-script METAFONT
fonts in the CTAN **schulschriften** package by Walter Entenmann (LPPL 1.3c,
see [`lppl/LPPL.txt`](./lppl/LPPL.txt) and [`ATTRIBUTION.txt`](./ATTRIBUTION.txt)).

The source lives at <https://ctan.org/tex-archive/fonts/schulschriften>; the
per-script TeX drivers are under `tex/<font>/` and the `.mf` sources under
`source/<font>/` (mirrored in [`metafont-source/`](./metafont-source)).

## The five scripts

| CSS `font-family`                    | short | script                                     | source |
|--------------------------------------|-------|--------------------------------------------|--------|
| `Suetterlinschrift Entenmann`        | su    | Sütterlinschrift (SU, 1911)                | wesu   |
| `Deutsche Normalschrift Entenmann`   | dn    | Deutsche Normalschrift (DN, 1941)          | wedn   |
| `Lateinische Ausgangsschrift Entenmann` | la | Lateinische Ausgangsschrift (LA, 1953)     | wela   |
| `Schulausgangsschrift Entenmann`     | sas   | Schulausgangsschrift (SAS, ex-DDR 1968)    | wesa   |
| `Vereinfachte Ausgangsschrift Entenmann` | va | Vereinfachte Ausgangsschrift (VA, 1972)    | weva   |

## Bold & italic?

Yes. Each script ships nine style drivers: a regular pen plus four weights
selected by the METAFONT `fetter` variable — `sb` semi-bold, `bx` bold,
`eb` extra-bold, `ub` ultra-bold — and an oblique `sl` (`slant:=0.325`, a real
geometric slant, not synthetic), with weight+slant combinations.

We build the CSS **RIBBI** set per family (regular / bold / italic /
bold-italic = `<none>` / `bx` / `sl` / `bxsl`) into [`faces/`](./faces),
20 files. Verified: bold thickens the stems (ink box 528→559) and italic adds
a genuine slant (width 528→585 at unchanged height). The extra weights
(`sb`, `eb`, `ub`) can be produced the same way on request.

## Contents

| Path | Purpose |
|---|---|
| `faces/entenmann-<short>-<style>.{ttf,woff2}` | the 20 usable faces |
| `metafont-source/<font>/*.mf` | original METAFONT sources (CTAN v5) |
| `lppl/LPPL.txt` | license full text |
| `ATTRIBUTION.txt` | attribution + compliance + limitations |
| `preview.html` | browser test page (open directly, no server) |
| `work/` | reproducible build scripts |

## Use in the app / website

Each family is a normal RIBBI family, so `font-weight: bold` / `font-style: italic`
select the right face automatically once you declare all four `@font-face`s.
Copy the wanted `faces/*.woff2` into `public/fonts/` (or use `next/font/local`):

```css
@font-face {
  font-family: "Lateinische Ausgangsschrift Entenmann";
  font-style: normal; font-weight: 400;
  src: url("/fonts/entenmann-la-regular.woff2") format("woff2");
}
@font-face {
  font-family: "Lateinische Ausgangsschrift Entenmann";
  font-style: normal; font-weight: 700;
  src: url("/fonts/entenmann-la-bold.woff2") format("woff2");
}
/* ... italic (400) and bold-italic (700) likewise ... */
```

Note: word-initial/word-final glyph variants of the original are driven by TeX
ligature tables and are NOT active in plain-text mode — see ATTRIBUTION.txt.

## Reproducing the build (WSL Ubuntu)

```sh
# 0) apt install texlive-binaries texlive-base texlive-fonts-recommended \
#      mftrace potrace t1utils fontforge python3-fonttools python3-brotli
bash work/01_download.sh          # fetch + unzip CTAN package into /tmp/wela-work
bash work/10_build_all.sh         # mf -> mftrace -> fontforge -> fontTools -> faces/
python3 work/12_verify_faces.py   # sanity-check weight/slant differences
```

`10_build_all.sh` is idempotent (re-uses already-traced `.pfa`), so tweaking
names/styles and re-running is fast.

Gotchas learned (baked into the scripts):
* Plain `mf jobname` defaults to `coldfit` mode (`fontmaking=0`) and writes
  **no tfm**; use `\mode:=lexmarks` so mftrace gets its tfm.
* mftrace needs a **clean dir with only that family's `.mf` + the `.tfm`** — a
  stale `*.NNNNgf` in cwd makes it try to "input" the bitmap as MF source.
* Native FontForge scripts have **no** `StyleBold`/`StyleItalic`; RIBBI
  `fsSelection` + `head.macStyle` + name IDs 1/2/4/6/16/17 are set in fontTools
  (`work/11_style_woff2.py`) instead.
