# mortgage-lending-analytics

Portfolio analytics project on US mortgage lending data.

## Current primary focus

Consumer mortgage credit risk and lender portfolio analytics using the HMDA Loan Application Register joined to FFIEC Call Report bank financials. Secondary questions explored as extensions: fair lending disparity patterns, geographic lending coverage for CRA assessment areas, peer-bank benchmarking, macro overlay with FRED indicators.

## Why this matters

Under the Home Mortgage Disclosure Act, every regulated US lender reports mortgage application-level data that becomes public. The dataset covers roughly 15 million applications per year across 5,000 or more institutions. It is the primary source that bank credit officers, compliance teams, market analysts, and federal regulators use to understand the US mortgage market, measure competitive positioning, evaluate concentration risk, and monitor fair lending outcomes.

FFIEC Call Reports add quarterly bank-level financials for every FDIC-insured institution, making it possible to analyze lender portfolios anchored in each bank's own balance sheet.

This project builds a reproducible analytics platform that:

1. Ingests multi-year HMDA LAR and FFIEC Call Report data
2. Harmonizes schema drift across reporting years (HMDA restructured in 2018)
3. Joins HMDA reporters to FFIEC institutions via LEI and RSSD identifiers
4. Delivers lender-level and market-level analytics including denial rate patterns, loan concentration metrics, and pricing spreads
5. Surfaces findings via dashboards consumable by a credit risk or compliance audience

## Stack

Snowflake, dbt, Tableau, Power BI, BigQuery, Azure Fabric, Python, SQL.

## Datasets

1. HMDA LAR (Loan Application Register), CFPB. Free public API at ffiec.cfpb.gov. Multi-year coverage starting 2018 in the current reporting format.
2. FFIEC Call Reports, FFIEC Central Data Repository (CDR). Free with free account registration. Quarterly bank financial data for every FDIC-insured institution.
3. Optional: FRED macro indicators (mortgage rates, unemployment, HPI) for economic overlay.

Dataset characteristics this project embraces rather than papers over:

- Schema changes across reporting years (HMDA was restructured in 2018 under Regulation C revisions)
- Lender-level reporting quality variance (small reporters vs large reporters)
- Regulator edit flags and correction resubmissions
- Missing fields across roughly half the HMDA column set
- Joining HMDA to FFIEC requires fuzzy institution matching where LEI to RSSD mapping is incomplete
- Call Report field additions and deletions across quarters

## Repo layout

See /docs/project-plan.md for full milestone structure.

Top-level:
- /docs: written artifacts
- /data: local data working area (gitignored)
- /notebooks: exploratory analysis
- /sql: standalone SQL scripts
- /dbt: dbt project root
- /dashboards: Tableau and Power BI source files
- /tests: Python and Great Expectations suites
- /scripts: ingestion and utility scripts

## Project status

Milestone 1 (Discovery) in progress. See /docs/project-plan.md for detailed milestone tracking.

## How to reproduce

Runbook will live at /docs/runbook.md once the pipeline is built and validated.

## License and data use

Code: MIT (proposed). Data: HMDA and FFIEC Call Reports are public and may be redistributed under each agency's terms. Published dashboards include source attribution.
