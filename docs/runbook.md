# Runbook

How to operate this pipeline from a cold clone and reproduce the dashboards, the validation numbers, and the SYB case study. This file is the operational contract. If a step here does not work on a fresh machine, it is a defect to fix in the runbook, not a workaround to remember.

## Environment

- macOS (Darwin) or Linux (Ubuntu 22.04 verified) or WSL2 on Windows
- Python 3.13 (Python 3.14 has known library-linking issues on macOS; stick with 3.13)
- Git 2.40 or later
- Internet access (downloads pull from CFPB, FFIEC, Federal Reserve, Census)

## First-time setup

```bash
# 1. Clone and enter
git clone git@github.com:thegeshwar/mortgage-lending-analytics.git
cd mortgage-lending-analytics

# 2. Python environment
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Verify install
python -c "import duckdb, pandas, polars, requests, tqdm; print('ok')"
```

## Data acquisition

### HMDA LAR (automated)

```bash
python scripts/download_hmda.py --years 2022 2023 2024
```

Expected output: three CSV files under `data/raw/hmda/{year}/{year}_public_lar_nationwide.csv` plus filer roster JSONs. Roughly 15 GB total, 15 to 25 minutes on a typical connection. Manifest written to `data/raw/hmda/_manifest.json`.

### FFIEC Call Reports (form-gated portal)

The CDR portal at https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx is ASP.NET WebForms and does not expose stable direct-download URLs. Download manually:

1. Browse to the portal.
2. Under "Available Products", confirm "Call Reports -- Single Period" is selected.
3. For each of 12 periods (20220331, 20220630, 20220930, 20221231 through 20241231), select the date in the "Reporting Period End Date" dropdown.
4. Confirm "Tab Delimited" format.
5. Click "Download". Wait for the `.zip` to finish saving (Chrome marks in-progress files with `.crdownload`).
6. Place each zip under `data/raw/ffiec_cdr/{yyyymmdd}/`.
7. Run the validator to register the files:

```bash
python scripts/download_ffiec_cdr.py --periods 20220331 20220630 20220930 20221231 20230331 20230630 20230930 20231231 20240331 20240630 20240930 20241231
```

### FFIEC NIC Institution Data (form-gated, 5 files)

Browse to https://www.ffiec.gov/npw/FinancialReport/DataDownload. Under **CSV Download**, click each of the 5 ZIP buttons:

- Attributes - Active
- Attributes - Closed
- Attributes - Branches
- Relationships
- Transformations

Place each zip under `data/raw/nic/`. Then run:

```bash
python scripts/download_nic.py
```

### OMB CBSA delineation (manual, small)

Browse to https://www.census.gov/programs-surveys/metro-micro/about/delineation-files.html. Download the most recent delineation Excel file. Save to `data/raw/cbsa/list1_{vintage}.xlsx`. Documented vintage pin in `/docs/data-quality-notes.md`.

### FRED macro (optional)

Requires a free FRED API key from https://fred.stlouisfed.org/docs/api/api_key.html. Save to `.env` as `FRED_API_KEY=...`. Script pending at Milestone 3 extension.

## Notebook execution

```bash
jupyter lab notebooks/
```

Notebooks run in this order:

1. `01-hmda-schema-and-quality.ipynb` (M2 deliverable, issue #1)
2. `02-hmda-distributions-and-demographics.ipynb` (M2 deliverable, issue #2)
3. `03-lender-and-market-structure.ipynb` (M2 deliverable, issue #3)
4. `04-callreport-profile-and-join-feasibility.ipynb` (M2 deliverable, issue #4)

Each notebook exports an HTML render to `/notebooks/exports/` when executed end to end. To regenerate the exports from the command line:

```bash
for nb in notebooks/0[1-4]-*.ipynb; do
  jupyter nbconvert --to notebook --execute "$nb" --output "$(basename $nb)"
  jupyter nbconvert --to html "$nb" --output-dir notebooks/exports/
done
```

## dbt pipeline (once M3 begins)

Not yet operational. Will follow this pattern when staged:

```bash
cd dbt
cp profiles.yml.example profiles.yml  # fill in Snowflake credentials
dbt deps
dbt seed
dbt run --select staging
dbt run --select intermediate
dbt run --select marts
dbt test
```

## Dashboard publish

### Tableau Public

1. Open `dashboards/tableau/mortgage-lending.twb` in Tableau Public Desktop.
2. Refresh data sources against the published marts (Snowflake share or exported CSV).
3. File > Save to Tableau Public. URL pinned in README once published.

### Power BI Service

1. Open `dashboards/powerbi/mortgage-lending.pbix` in Power BI Desktop.
2. Refresh queries against the same marts.
3. Publish to Power BI Service. URL pinned in README once published.

## Validation spot checks

After a full rebuild, verify these anchor numbers:

- HMDA 2024 total rows: 12,229,298
- HMDA 2024 origination count (action_taken = 1): 6,176,052
- SYB 2024 total applications under LEI 4LJGQ9KJ9S0CP4B1FY29: 3,447
- SYB 2024 originations: 2,255

If any of these drift, investigate before proceeding. Most likely cause: the HMDA vintage on disk differs from the one pinned in the manifest.

## Common failures

### Python 3.14 ensurepip failure on macOS

`python3 -m venv .venv` fails with an ensurepip error. Cause: Python 3.14 on Homebrew has a dynamic-link issue with system libexpat. Fix: use `python3.13 -m venv .venv` instead.

### HMDA S3 URL returns 403

The direct S3 bucket `s3.amazonaws.com/cfpb-hmda-public/...` is no longer public-listable. The script uses the `ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/csv` endpoint, which is the supported path. If this changes, update `LAR_URL_PATTERN` in `scripts/download_hmda.py`.

### FFIEC CDR zips are truncated

Chrome sometimes truncates CDR downloads mid-stream. Symptom: a `.zip` without an end-of-central-directory record (verified with `python -c "import zipfile; zipfile.ZipFile('...').namelist()"`). Fix: redownload, letting the file fully save (Chrome marks incomplete files with `.crdownload` suffix).

### LEI not found in HMDA filer roster

Either the LEI is from a pre-2018 filer or has been consolidated in a merger. Check the NIC institution event history. SYB's LEI 4LJGQ9KJ9S0CP4B1FY29 has been stable since 2018.

## Updating vintages

When re-pulling HMDA or Call Report data for a later point in time:

1. Rename the existing `data/raw/{source}/_manifest.json` to `_manifest.{YYYYMMDD}.json`
2. Run the downloader with `--force`
3. Compare checksums. Any unexpected delta (especially for historical periods) indicates a regulator restatement worth a dated entry in `data-quality-notes.md`
