#!/bin/bash
# Auto-moves FFIEC CDR and NIC zips from ~/Downloads into data/raw/ as they land.
# Skips files still being downloaded (.crdownload).
set -u
REPO="/Users/thegeshwar/mortgage-lending-analytics"
DL="$HOME/Downloads"

shopt -s nullglob 2>/dev/null || true

while true; do
  for f in "$DL"/FFIEC\ CDR\ Call\ Bulk*.zip; do
    [ -f "$f" ] || continue
    # Skip if Chrome is still writing (crdownload sibling exists)
    if [ -f "$f.crdownload" ] || [ -f "${f%.zip}.crdownload" ]; then
      continue
    fi
    base=$(basename "$f")
    date=$(echo "$base" | grep -oE '[0-9]{8}' | head -1)
    if [ -n "$date" ]; then
      mm="${date:0:2}"; dd="${date:2:2}"; yyyy="${date:4:4}"
      period="${yyyy}${mm}${dd}"
      mkdir -p "$REPO/data/raw/ffiec_cdr/$period"
      mv "$f" "$REPO/data/raw/ffiec_cdr/$period/$base"
      echo "[moved] $base -> ffiec_cdr/$period/"
    fi
  done
  for f in "$DL"/CSV_ATTRIBUTES_ACTIVE.zip "$DL"/CSV_ATTRIBUTES_CLOSED.zip "$DL"/CSV_ATTRIBUTES_BRANCHES.zip "$DL"/CSV_RELATIONSHIPS.zip "$DL"/CSV_TRANSFORMATIONS.zip; do
    [ -f "$f" ] || continue
    if [ -f "$f.crdownload" ] || [ -f "${f%.zip}.crdownload" ]; then
      continue
    fi
    mv "$f" "$REPO/data/raw/nic/"
    echo "[moved] $(basename "$f") -> nic/"
  done
  sleep 3
done
