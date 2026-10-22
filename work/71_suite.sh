#!/usr/bin/env bash
# Run every check the font build has, so a fix to one stage cannot quietly break
# another. Each script prints its own verdict; this only keeps them together.
#
# The faces are named here instead of being left to each script's default: they
# are written to ../faces, and a check whose default path does not exist reads
# nothing and reports nothing - a green line that means nothing at all.
cd "$(dirname "$0")"
FACES=(../faces/entenmann-{su,dn,la,sas,va}-regular.ttf)
run() { echo "===== $1"; shift; python3 "$@" 2>&1 | tail -12; }
run 54_fmt          54_fmt.py "${FACES[@]}"
run 55_fmt2         55_fmt2.py
run 56_wordend      56_wordend.py ../faces/entenmann-la-regular.ttf
run 57_parse_audit  57_parse_audit.py
run 59_join_audit   59_join_audit.py
run 60_wordwidth    60_wordwidth.py
run 62_slot_audit   62_slot_audit.py
run 66_tfm_widths   66_tfm_widths.py
run 78_shipped_faces 78_shipped_faces.py
