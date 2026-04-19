"""Download HMDA Snapshot Loan Application Register (LAR) and filer panel.

Source: Consumer Financial Protection Bureau HMDA Data Publication API.
The CFPB exposes the Snapshot LAR via the public data-browser API at
ffiec.cfpb.gov/v2/data-browser-api. This script pulls the full nationwide
LAR plus the filer (panel) roster per year.

Endpoints used:
    LAR (CSV, large):   /v2/data-browser-api/view/nationwide/csv?years={year}
    Filers (JSON):      /v2/reporting/filers/{year}

File sizes (approximate, uncompressed):
    2022 LAR CSV:  ~6 GB
    2023 LAR CSV:  ~4 GB
    2024 LAR CSV:  ~4.6 GB

Usage:
    python scripts/download_hmda.py --years 2022 2023 2024
    python scripts/download_hmda.py --years 2024 --assets filers
    python scripts/download_hmda.py --years 2023 --force

Steward discipline: every download writes a manifest entry recording
source URL, sha256 checksum, byte size, and download timestamp. The
manifest is the record of truth for vintage pinning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "raw" / "hmda"
MANIFEST_PATH = DATA_DIR / "_manifest.json"

LAR_URL_PATTERN = (
    "https://ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/csv?years={year}"
)
FILERS_URL_PATTERN = "https://ffiec.cfpb.gov/v2/reporting/filers/{year}"

ASSET_SPEC = {
    "lar": {
        "url_pattern": LAR_URL_PATTERN,
        "filename": "{year}_public_lar_nationwide.csv",
        "format": "csv",
        "approx_bytes": 5_000_000_000,
    },
    "filers": {
        "url_pattern": FILERS_URL_PATTERN,
        "filename": "{year}_public_filers.json",
        "format": "json",
        "approx_bytes": 500_000,
    },
}

CHUNK_SIZE = 4 << 20  # 4 MiB


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {"entries": []}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def record_manifest_entry(
    manifest: dict,
    year: int,
    asset: str,
    url: str,
    dest: Path,
) -> None:
    entry = {
        "year": year,
        "asset": asset,
        "source_url": url,
        "local_path": str(dest.relative_to(REPO_ROOT)),
        "sha256": sha256_of_file(dest),
        "bytes": dest.stat().st_size,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest["entries"] = [
        e for e in manifest["entries"]
        if not (e.get("year") == year and e.get("asset") == asset)
    ]
    manifest["entries"].append(entry)
    manifest["entries"].sort(key=lambda e: (e["year"], e["asset"]))


def stream_download(url: str, dest: Path, approx_bytes: int | None = None) -> None:
    """Download with a progress bar, atomic via .part rename. Long timeout for LAR."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=(30, 600)) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0)) or approx_bytes
        with tmp.open("wb") as f, tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            desc=dest.name,
            leave=True,
        ) as bar:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
    tmp.replace(dest)


def download_asset(year: int, asset: str, force: bool) -> bool:
    spec = ASSET_SPEC[asset]
    url = spec["url_pattern"].format(year=year)
    dest = DATA_DIR / str(year) / spec["filename"].format(year=year)

    if dest.exists() and not force:
        print(f"[skip] {asset} {year}: already present at {dest.relative_to(REPO_ROOT)} ({dest.stat().st_size:,} bytes)")
        return True

    print(f"[get]  {asset} {year}: {url}")
    try:
        stream_download(url, dest, spec.get("approx_bytes"))
    except requests.HTTPError as e:
        print(f"[fail] {asset} {year}: HTTP {e.response.status_code}")
        return False
    except requests.RequestException as e:
        print(f"[fail] {asset} {year}: {type(e).__name__}: {e}")
        return False

    size = dest.stat().st_size
    print(f"[ok]   {asset} {year}: {size:,} bytes")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        required=True,
        help="HMDA activity years to download",
    )
    parser.add_argument(
        "--assets",
        nargs="+",
        choices=list(ASSET_SPEC.keys()),
        default=list(ASSET_SPEC.keys()),
        help="Which HMDA assets to fetch. Default: all.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if local file exists",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    failures: list[tuple[int, str]] = []

    for year in args.years:
        for asset in args.assets:
            ok = download_asset(year, asset, args.force)
            if not ok:
                failures.append((year, asset))
                continue
            spec = ASSET_SPEC[asset]
            dest = DATA_DIR / str(year) / spec["filename"].format(year=year)
            if dest.exists():
                record_manifest_entry(
                    manifest,
                    year,
                    asset,
                    spec["url_pattern"].format(year=year),
                    dest,
                )

    save_manifest(manifest)

    if failures:
        print(f"\n{len(failures)} asset(s) failed: {failures}", file=sys.stderr)
        print(
            "If an endpoint has changed, probe the publication API at "
            "ffiec.cfpb.gov/v2/ or download manually from "
            "ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset.",
            file=sys.stderr,
        )
        return 1

    print(f"\nManifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
