"""Validate and register FFIEC Call Report bulk files.

Source: FFIEC Central Data Repository Public Data Distribution.
Portal: https://cdr.ffiec.gov/public/

The CDR bulk download is served behind an interactive form (report period,
reporting series, format). There is no stable direct URL per period, so this
script does not auto-download. Instead, it:

1. Prints the exact steps to download for a given period.
2. Validates files placed under data/raw/ffiec_cdr/<period>/.
3. Records a manifest entry per period with sha256, byte size, and schedule
   file inventory so vintage pinning is preserved.

Periods are represented as YYYYMMDD of the quarter-end date:
    Q1 -> 0331, Q2 -> 0630, Q3 -> 0930, Q4 -> 1231

Example:
    python scripts/download_ffiec_cdr.py --periods 20231231 20240331

Steward discipline: CDR is restated for up to four quarters after filing.
The manifest records the acquisition date so a future reproduction knows
which vintage was used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "raw" / "ffiec_cdr"
MANIFEST_PATH = DATA_DIR / "_manifest.json"

CHUNK_SIZE = 1 << 20

DOWNLOAD_INSTRUCTIONS = """
Manual download steps for FFIEC Call Report period {period}:

  1. Browse to https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx
  2. Under "Download Bulk Data", select:
       Series:   Call Reports - Single Period
       Period:   {period_display}
       File Format: Tab Delimited
  3. Click "Download" and save the resulting zip.
  4. Place the downloaded zip at:
       data/raw/ffiec_cdr/{period}/FFIEC_CDR_Call_Bulk_POD_{period}.zip
     (exact filename from the portal is fine; the script discovers whatever
     zip is present in that directory)
  5. Re-run this script with --periods {period} to validate and register.
"""


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {"entries": []}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def period_display(period: str) -> str:
    """20231231 -> '12/31/2023'."""
    if len(period) != 8 or not period.isdigit():
        return period
    return f"{period[4:6]}/{period[6:8]}/{period[0:4]}"


def validate_period(period: str, manifest: dict) -> bool:
    period_dir = DATA_DIR / period
    if not period_dir.exists() or not any(period_dir.iterdir()):
        print(DOWNLOAD_INSTRUCTIONS.format(period=period, period_display=period_display(period)))
        return False

    zips = sorted(period_dir.glob("*.zip"))
    if not zips:
        print(f"[fail] {period}: no .zip found under {period_dir.relative_to(REPO_ROOT)}")
        print(DOWNLOAD_INSTRUCTIONS.format(period=period, period_display=period_display(period)))
        return False

    for zip_path in zips:
        sha = sha256_of_file(zip_path)
        size = zip_path.stat().st_size
        print(f"[ok]   {period}: {zip_path.name} {size:,} bytes sha256={sha[:12]}...")

        manifest["entries"] = [
            e for e in manifest["entries"]
            if not (e.get("period") == period and e.get("filename") == zip_path.name)
        ]
        manifest["entries"].append({
            "period": period,
            "period_display": period_display(period),
            "filename": zip_path.name,
            "local_path": str(zip_path.relative_to(REPO_ROOT)),
            "sha256": sha,
            "bytes": size,
            "registered_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "FFIEC CDR Public Data Distribution",
            "source_url": "https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx",
        })

    manifest["entries"].sort(key=lambda e: (e["period"], e["filename"]))
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--periods",
        nargs="+",
        required=True,
        help="Quarter-end dates in YYYYMMDD form, e.g. 20231231 20240331",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    missing: list[str] = []

    for period in args.periods:
        ok = validate_period(period, manifest)
        if not ok:
            missing.append(period)

    save_manifest(manifest)

    if missing:
        print(
            f"\n{len(missing)} period(s) awaiting manual download: {missing}",
            file=sys.stderr,
        )
        return 1

    print(f"\nManifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
