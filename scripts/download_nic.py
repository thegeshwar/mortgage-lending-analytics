"""Download FFIEC National Information Center (NIC) institution reference data.

NIC is the authoritative crosswalk between banking identifiers: RSSD,
FDIC certificate, OCC charter, and LEI. It is the bridge that lets HMDA
LAR (LEI-keyed post-2018) join to FFIEC Call Reports (RSSD-keyed).

Source: FFIEC NIC bulk data downloads.
Portal: https://www.ffiec.gov/npw/FinancialReport/DataDownload

The NIC bulk downloads are served behind an interactive form. This script
validates locally-placed files and registers them in a manifest, mirroring
the FFIEC CDR downloader pattern.

Assets tracked:
    - CSV_ATTRIBUTES_ACTIVE.zip:    active institution attributes (one row per active RSSD)
    - CSV_ATTRIBUTES_CLOSED.zip:    closed institution attributes (one row per defunct RSSD)
    - CSV_ATTRIBUTES_BRANCH.zip:    branch-level attributes
    - CSV_RELATIONSHIPS.zip:        parent-subsidiary-affiliate relationships

Example:
    python scripts/download_nic.py --assets attributes_active relationships
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "raw" / "nic"
MANIFEST_PATH = DATA_DIR / "_manifest.json"

CHUNK_SIZE = 1 << 20

ASSET_FILENAMES = {
    "attributes_active": "CSV_ATTRIBUTES_ACTIVE.zip",
    "attributes_closed": "CSV_ATTRIBUTES_CLOSED.zip",
    "attributes_branches": "CSV_ATTRIBUTES_BRANCHES.zip",
    "relationships": "CSV_RELATIONSHIPS.zip",
    "transformations": "CSV_TRANSFORMATIONS.zip",
}

DOWNLOAD_INSTRUCTIONS = """
Manual download steps for NIC {asset}:

  1. Browse to https://www.ffiec.gov/npw/FinancialReport/DataDownload
  2. Under "National Information Center Bulk Data Download", select:
       Download Type: {asset_display}
       Output Format: CSV
  3. Click "Download" and save the resulting zip.
  4. Place the downloaded zip at:
       data/raw/nic/{filename}
  5. Re-run this script with --assets {asset} to validate and register.
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


def validate_asset(asset: str, manifest: dict) -> bool:
    filename = ASSET_FILENAMES[asset]
    path = DATA_DIR / filename

    if not path.exists():
        print(DOWNLOAD_INSTRUCTIONS.format(
            asset=asset,
            asset_display=asset.replace("_", " ").title(),
            filename=filename,
        ))
        return False

    sha = sha256_of_file(path)
    size = path.stat().st_size
    print(f"[ok]   nic/{asset}: {filename} {size:,} bytes sha256={sha[:12]}...")

    manifest["entries"] = [
        e for e in manifest["entries"] if e.get("asset") != asset
    ]
    manifest["entries"].append({
        "asset": asset,
        "filename": filename,
        "local_path": str(path.relative_to(REPO_ROOT)),
        "sha256": sha,
        "bytes": size,
        "registered_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "FFIEC National Information Center",
        "source_url": "https://www.ffiec.gov/npw/FinancialReport/DataDownload",
    })
    manifest["entries"].sort(key=lambda e: e["asset"])
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--assets",
        nargs="+",
        choices=list(ASSET_FILENAMES.keys()),
        default=list(ASSET_FILENAMES.keys()),
        help="Which NIC assets to validate. Default: all five.",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    missing: list[str] = []

    for asset in args.assets:
        if not validate_asset(asset, manifest):
            missing.append(asset)

    save_manifest(manifest)

    if missing:
        print(f"\n{len(missing)} asset(s) awaiting manual download: {missing}", file=sys.stderr)
        return 1

    print(f"\nManifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
