#!/bin/bash
# What can turn a PDF into a viewable image on this machine?
for t in pdftoppm pdftotext pdfinfo gs mutool convert magick qpdf python3; do
  printf '%-10s %s\n' "$t" "$(command -v $t || echo '-')"
done
echo "--- python pdf modules ---"
python3 - <<'PY'
for m in ("fitz", "pypdf", "PyPDF2", "pdf2image", "PIL"):
    try:
        __import__(m)
        print(m, "OK")
    except Exception as e:
        print(m, "no", type(e).__name__)
PY
echo "--- apt availability ---"
apt-cache policy poppler-utils 2>/dev/null | head -5 || echo "no apt-cache"
