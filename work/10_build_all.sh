#!/usr/bin/env bash
# Build all five Schulschriften into web faces (regular/bold/italic/bold-italic).
# Each script family ships METAFONT drivers for:
#   weights: (none)=regular, sb=semi-bold, bx=bold, eb=extra-bold, ub=ultra-bold  (pen `fetter`)
#   slant:   sl = "italic" (oblique via `currenttransform slanted 0.325`), plus <weight>sl combos
# We emit the CSS quadruple per family: regular, bold(bx), italic(sl), bold-italic(bxsl).
set -uo pipefail

SRCROOT=/tmp/wela-work/schulschriften/source
BUILD=/tmp/build
ENC=/usr/share/texlive/texmf-dist/fonts/enc/dvips/base/tex256.enc
OUT_WIN="/mnt/c/Users/yanan/code/fms-app/font/faces"
# idempotent: reuse existing traced .pfa so re-runs are fast
mkdir -p "$BUILD" "$OUT_WIN"

# parallel arrays: mf prefix | file short | LPPL-safe family name | PS upper
MF=(wesu wedn wela wesa weva)
SHORT=(su dn la sas va)
FAM=("Suetterlinschrift Entenmann" \
     "Deutsche Normalschrift Entenmann" \
     "Lateinische Ausgangsschrift Entenmann" \
     "Schulausgangsschrift Entenmann" \
     "Vereinfachte Ausgangsschrift Entenmann")
UP=(SU DN LA SAS VA)

# style drivers: suffix | subfamily | ps-suffix | file-tag | bold | italic
SDRV=(14 bx14 sl14 bxsl14)
SSUB=("Regular" "Bold" "Italic" "Bold Italic")
SPS=(Regular Bold Italic BoldItalic)
SFILE=(regular bold italic bold-italic)
SBOLD=(0 1 0 1)
SITAL=(0 0 1 1)

PE="$BUILD/convert.pe"
: > "$PE"
FACES=()   # collect "ttf" paths for the woff2 pass

for i in "${!MF[@]}"; do
  prefix="${MF[$i]}"; short="${SHORT[$i]}"; fam="${FAM[$i]}"; up="${UP[$i]}"
  work="$BUILD/$prefix"
  rm -rf "$work"; mkdir -p "$work"
  cp "$SRCROOT/$prefix"/*.mf "$work"/
  cd "$work" || { echo "SKIP $prefix (no dir)"; continue; }
  for j in "${!SDRV[@]}"; do
    drv="${prefix}${SDRV[$j]}"
    psname="Entenmann${up}-${SPS[$j]}"
    sub="${SSUB[$j]}"
    slug="entenmann-${short}-${SFILE[$j]}"
    echo "### building $drv  ($fam / $sub)"
    # 2) clean dir: only that family's .mf + this tfm, then mftrace -> .pfa
    tdir="$BUILD/trace_${drv}"; mkdir -p "$tdir"
    cp "$work"/*.mf "$tdir"/ 2>/dev/null
    if [ ! -f "$tdir/$drv.pfa" ]; then
      # 1) tfm + bitmap at high res (lexmarks => fontmaking=1 writes the tfm mftrace needs)
      mf "\\mode:=lexmarks; nonstopmode; input $drv" >/dev/null 2>&1
      cp "$work"/*.mf "$work/$drv.tfm" "$tdir"/ 2>/dev/null
      ( cd "$tdir" && mftrace --keep --encoding="$ENC" --magnification=1600 "$drv.mf" >/dev/null 2>&1 )
    fi
    if [ ! -f "$tdir/$drv.pfa" ]; then echo "  !! mftrace failed for $drv"; continue; fi
    # 3) queue a FontFace convert (native fontforge pass) -> TTF into faces/
    #    bold/italic style bits + name table are applied later in fontTools,
    #    because native fontforge has no StyleBold/StyleItalic script function.
    full="$fam $sub"
    {
      echo "Open(\"$tdir/$drv.pfa\")"
      echo "SelectAll()"
      echo "ScaleToEm(1000)"
      echo "SetFontNames(\"$psname\", \"$fam\", \"$full\", \"$sub\")"
      echo "Generate(\"$OUT_WIN/$slug.ttf\")"
      echo "Close()"
    } >> "$PE"
    FACES+=("$OUT_WIN/$slug.ttf")
    echo "  ok -> $slug"
  done
done

# 4) one fontforge process does all the outline renames + TTF generation
fontforge -script "$PE" >/dev/null 2>&1

# 5) apply RIBBI style bits + name table, then TTF -> WOFF2
python3 /mnt/c/Users/yanan/code/fms-app/font/work/11_style_woff2.py "$OUT_WIN"

echo "=== faces dir:"
ls -la "$OUT_WIN"
