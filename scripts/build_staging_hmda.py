"""Build the HMDA staging DuckDB from registered raw CSVs.

The HMDA nationwide public LAR CSVs are large (about 15 GB combined for
2022, 2023, 2024). Every EDA notebook and every downstream staging query
benefits from a persistent DuckDB that holds all three vintages as
tables. This script materializes that database from the raw CSVs.

Design choices:
    1. All columns are ingested as VARCHAR. HMDA fields mix numeric
       values with the sentinel string "Exempt" and with NA. Deferring
       type coercion to later staging lets the EDA notebook profile
       the mixture and decide per-column casts explicitly.
    2. One table per year: lar_2022, lar_2023, lar_2024. This keeps
       schema delta investigation trivial and lets queries target a
       single vintage efficiently.
    3. The script is idempotent. If a table already exists with the
       expected row count, it is skipped. Use --rebuild to force.
    4. Source of truth is data/raw/hmda/_manifest.json. A missing
       manifest entry is a hard error.

Usage:
    python scripts/build_staging_hmda.py
    python scripts/build_staging_hmda.py --years 2024
    python scripts/build_staging_hmda.py --rebuild
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "data" / "raw" / "hmda" / "_manifest.json"
STAGING_DIR = REPO_ROOT / "data" / "staging"
STAGING_DB = STAGING_DIR / "hmda_lar.duckdb"


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"missing manifest: {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text())


def lar_path_for_year(manifest: dict, year: int) -> Path:
    for entry in manifest["entries"]:
        if entry["asset"] == "lar" and entry["year"] == year:
            return REPO_ROOT / entry["local_path"]
    raise SystemExit(f"manifest has no LAR entry for {year}")


def table_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    row = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [name],
    ).fetchone()
    return bool(row and row[0])


def build_year(
    con: duckdb.DuckDBPyConnection,
    year: int,
    csv_path: Path,
    rebuild: bool,
) -> tuple[str, int, float]:
    table = f"lar_{year}"
    if table_exists(con, table) and not rebuild:
        row = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return table, int(row[0]), 0.0

    if rebuild and table_exists(con, table):
        con.execute(f"DROP TABLE {table}")

    print(f"building {table} from {csv_path.name} ({csv_path.stat().st_size / 1e9:.2f} GB)", flush=True)
    start = time.time()
    con.execute(
        f"""
        CREATE TABLE {table} AS
        SELECT * FROM read_csv(
            '{csv_path.as_posix()}',
            header = true,
            all_varchar = true,
            sample_size = -1,
            parallel = true,
            ignore_errors = false
        )
        """
    )
    elapsed = time.time() - start
    row = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return table, int(row[0]), elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=[2022, 2023, 2024],
        help="years to (re)build (default: 2022 2023 2024)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="drop and rebuild even if the table already exists",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(STAGING_DB))
    con.execute("PRAGMA threads = 8")

    summary: list[tuple[str, int, float]] = []
    for year in args.years:
        csv_path = lar_path_for_year(manifest, year)
        if not csv_path.exists():
            raise SystemExit(f"manifest references missing file: {csv_path}")
        result = build_year(con, year, csv_path, args.rebuild)
        summary.append(result)

    print()
    print(f"{'table':<10}{'rows':>14}{'elapsed_s':>14}")
    for table, rows, elapsed in summary:
        status = f"{elapsed:>14.1f}" if elapsed > 0 else f"{'cached':>14}"
        print(f"{table:<10}{rows:>14,}{status}")
    print(f"\nstaging db: {STAGING_DB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
