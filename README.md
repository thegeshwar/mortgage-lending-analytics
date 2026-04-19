# mortgage-lending-analytics

Portfolio analytics on US mortgage lending, anchored on Stock Yards Bank and Trust Company (Louisville, KY). Built with Lead IT Data Steward discipline: every metric is traceable from the dashboard back through the mart, the intermediate model, the staging layer, and the raw manifest. Every decision that shaped the output is dated in the data-quality log.

**Status**: Milestone 1 (Discovery) closed. Release: [v0.1.0-m1-discovery](https://github.com/thegeshwar/mortgage-lending-analytics/releases/tag/v0.1.0-m1-discovery). Milestone 2 (Planning) open with 10 tracked issues.

## The question

Which US mortgage lenders are extending the most credit risk relative to the financial cushion they are carrying, and how has that posture shifted year over year across geographies and borrower segments? See [/docs/problem-statement.md](docs/problem-statement.md) for the full framing and [/docs/stakeholder-personas.md](docs/stakeholder-personas.md) for the four audiences.

## What is in this repo

Three dashboards, produced from a dbt warehouse on top of public regulated data:

1. **Lender portfolio posture**: origination volume, concentration, demographic mix, and capital cushion for any lender with a peer group comparison
2. **MSA market structure**: HHI, top-5 share, lender class mix for any US metro area
3. **Applicant demographic lens**: fair-lending cut with standard HMDA-limitation disclaimers

Plus the governance artifacts underneath that make the dashboards defensible:
- [Data dictionary](docs/data-dictionary.md) covering every source column and every derived column
- [Data quality notes](docs/data-quality-notes.md) with dated decisions about schema drift, exempt-value handling, crosswalks, and reconciliation
- [Schema harmonization plan](docs/schema-harmonization-plan.md) for the HMDA 2018 Dodd-Frank restructure
- [Validation report](docs/validation-report.md) reconciling every published number to CFPB HMDA Data Browser or FFIEC UBPR aggregates

## Headline findings from the initial EDA

Verified against 39.9 million HMDA applications (2022, 2023, 2024) and 12 quarters of FFIEC Call Reports:

| Year | HMDA rows | Origination rate | Denial rate | Lender panel |
|------|----------:|-----------------:|------------:|-------------:|
| 2022 | 16,099,307 | 52.2% | 15.5% | 4,454 |
| 2023 | 11,564,178 | 49.4% | 17.6% | 5,093 |
| 2024 | 12,229,298 | 50.5% | 17.2% | 4,878 |

- **Stock Yards Bank and Trust origination rate steady at 65 percent**, roughly 15 percentage points above the market baseline. A cleanly observable pattern for the portfolio case study.
- **Top-10 market share is only 21 to 22 percent**, materially more diffuse than the "big five banks" narrative assumes. Supports a peer-group framing over a monolithic-lender framing.
- **Exempt-value reporting is consistently 2.33 percent** across every HMDA field that permits partial-exemption reporting, implying a fixed cohort of small reporters. Handled as a distinct category through staging rather than null-imputed.

## Stack

| Layer | Tool |
|-------|------|
| Warehouse | Snowflake (primary), BigQuery and Azure Fabric (comparative parallel builds) |
| Transformations | dbt Core |
| Languages | Python (pandas, polars, duckdb), SQL |
| BI | Tableau Public, Power BI Service |
| Data quality | dbt tests, Great Expectations |
| Version control | Git and GitHub |
| Project tracking | GitHub Milestones, Issues, Projects v2 board |

## Data sources (all public)

| Source | Grain | Cadence | Volume | License |
|--------|-------|---------|--------|---------|
| HMDA LAR (Snapshot) | Loan-application | Annual | ~4-6 GB/year CSV | Public, CFPB |
| FFIEC Call Reports | Bank-quarter | Quarterly | ~6 MB/period zip | Public, FFIEC |
| FFIEC NIC | Institution-level | Continuous | ~25 MB total | Public, Federal Reserve |
| OMB CBSA delineation | County-to-MSA | Annual revisions | ~2 MB | Public |
| FRED macro (optional) | Series-period | Varies | Small | FRED API terms, attribution required |

Full provenance, access methods, and known quirks in [/docs/data-sources.md](docs/data-sources.md).

## Repo layout

```
/docs          written artifacts (13 files, see below)
/data          raw/staging/processed (gitignored except manifests)
/notebooks     EDA and prototyping
/dbt           dbt project (models, seeds, tests, macros)
/sql           standalone warehouse setup and manual queries
/dashboards    Tableau and Power BI source files and exports
/tests         Python and Great Expectations test suites
/scripts       ingestion, setup, utility
```

Documentation set:

| File | Purpose |
|------|---------|
| [project-plan.md](docs/project-plan.md) | Five milestones, deliverables, DoD, Kanban lifecycle |
| [problem-statement.md](docs/problem-statement.md) | The analytical question and the artifact set |
| [data-sources.md](docs/data-sources.md) | Provenance for every source |
| [stakeholder-personas.md](docs/stakeholder-personas.md) | Four generic personas, no invented names |
| [data-quality-notes.md](docs/data-quality-notes.md) | Running log of dated decisions |
| [eda-plan.md](docs/eda-plan.md) | Four-notebook EDA specification |
| [glossary.md](docs/glossary.md) | Acronyms and domain terms |
| [runbook.md](docs/runbook.md) | Cold-clone reproduction steps |
| [velocity-log.md](docs/velocity-log.md) | Actual milestone start and end dates |
| [known-limitations.md](docs/known-limitations.md) | What this analysis cannot answer |
| [executive-summary.md](docs/executive-summary.md) | One-page pitch for reviewers |
| [methodology.md](docs/methodology.md) | Methodology writeup (builds through M5) |

## How to reproduce

Full steps in [/docs/runbook.md](docs/runbook.md). Short version:

```bash
git clone git@github.com:thegeshwar/mortgage-lending-analytics.git
cd mortgage-lending-analytics
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_hmda.py --years 2022 2023 2024
python scripts/download_ffiec_cdr.py --periods 20220331 20220630 20220930 20221231 20230331 20230630 20230930 20231231 20240331 20240630 20240930 20241231
python scripts/download_nic.py
jupyter lab notebooks/
```

## Live links

Will be populated as dashboards publish at Milestone 3.

- Tableau Public: _pending M3_
- Power BI Service: _pending M3_
- Methodology writeup (LinkedIn article): _pending M5_

## License

Code: [MIT](LICENSE). Data: HMDA and FFIEC Call Reports are public under each agency's redistribution terms. Published dashboards include source attribution per those terms.

## Contributing

Even for a solo project, every change follows a tracked workflow. See [CONTRIBUTING.md](CONTRIBUTING.md) and the GitHub workflow section of [CLAUDE.md](CLAUDE.md).
