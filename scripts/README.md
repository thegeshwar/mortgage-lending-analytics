# scripts/

Utility scripts for ingestion, setup, and housekeeping. Each script is idempotent where it can be and writes a manifest so vintage pinning is preserved.

## Ingestion scripts

### download_hmda.py

Downloads HMDA Snapshot LAR and related files (panel, transmittal sheet) for specified activity years.

```bash
python scripts/download_hmda.py --years 2022 2023 2024
python scripts/download_hmda.py --years 2024 --assets lar
python scripts/download_hmda.py --years 2023 --force
```

Output: zips land under `data/raw/hmda/<year>/`. A manifest at `data/raw/hmda/_manifest.json` records source URL, sha256, byte size, and download timestamp per asset.

### download_ffiec_cdr.py

The FFIEC CDR bulk portal is form-gated, so this script cannot fully automate. It prints manual download steps for each period, then validates and registers files once placed locally.

```bash
python scripts/download_ffiec_cdr.py --periods 20221231 20231231 20241231
```

Periods are quarter-end YYYYMMDD. Output manifest at `data/raw/ffiec_cdr/_manifest.json`.

### download_nic.py

Validates and registers NIC institution reference bulk files (attributes, relationships). Like the CDR portal, NIC is form-gated so this script prints steps for assets not yet present locally.

```bash
python scripts/download_nic.py
python scripts/download_nic.py --assets attributes_active relationships
```

Output manifest at `data/raw/nic/_manifest.json`.

## Typical first-time setup

```bash
# 1. Create virtualenv and install deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Pull HMDA snapshot for three most recent years
python scripts/download_hmda.py --years 2022 2023 2024

# 3. Pull NIC reference (walks you through the form-based download)
python scripts/download_nic.py

# 4. Pull FFIEC Call Reports for the matching periods (same form-based flow)
python scripts/download_ffiec_cdr.py --periods 20221231 20231231 20241231

# 5. Run initial EDA notebook
jupyter lab notebooks/01-initial-eda.ipynb
```

## Manifest format

Every download/validate step updates a JSON manifest under the relevant `data/raw/<source>/` directory. A manifest entry captures enough metadata to reproduce the state of the raw file:

- `source_url` or `source` (authoritative provenance)
- `local_path` (relative to repo root)
- `sha256` (integrity check)
- `bytes` (size sanity check)
- `downloaded_at_utc` or `registered_at_utc` (vintage timestamp)

Manifests are committed to git. Raw data files are not (`data/raw/*` is gitignored). This is intentional: the manifest is the vintage record, the data itself is reproducible from the source.
