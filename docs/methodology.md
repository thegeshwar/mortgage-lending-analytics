# Methodology

Long-form writeup of how this project was built. Target audience: a reader who wants to understand the reasoning behind every non-obvious choice, or who wants to reproduce the work from scratch.

This file grows as the project progresses. Milestone 5 produces the final publishable version (LinkedIn article, Medium post). The current state is a structured skeleton with each section filled as the underlying work completes.

## Table of contents

1. Question and framing
2. Data sources and vintage policy
3. Data acquisition
4. Schema harmonization
5. Entity resolution (LEI to RSSD)
6. Data quality rules
7. Warehouse model
8. Analytics: portfolio posture
9. Analytics: market structure
10. Analytics: applicant demographics
11. Validation and reconciliation
12. Known limitations
13. What would be different at scale

---

## 1. Question and framing

See /docs/problem-statement.md for the full question statement and persona-decision mapping. The short version: which US mortgage lenders are extending the most credit risk relative to their financial cushion, and how has that posture shifted.

The project is framed as a portfolio analytics build rather than a modeling exercise. Every metric is descriptive, reproducible from the raw public data, and reconciled to an independent benchmark.

## 2. Data sources and vintage policy

Five public sources, all free, documented in /docs/data-sources.md:

- HMDA Loan Application Register (Snapshot), CFPB, annual
- FFIEC Call Reports (forms 031, 041, 051), FFIEC CDR, quarterly
- FFIEC National Information Center institution data, Federal Reserve, continuous
- OMB Core-Based Statistical Area delineation, annual revisions
- FRED macro series (optional), Federal Reserve Bank of St. Louis

**Vintage pinning**: every download writes a manifest entry recording source URL, sha256, byte size, and acquisition timestamp. Manifests are git-tracked. Raw data files are not.

**Snapshot vs Modified LAR**: Snapshot is used exclusively. Modified LAR redacts selected fields for privacy and is not required when the project is run by the author on author-controlled infrastructure.

**As-filed vs restated Call Reports**: the most-recent available vintage is pulled at download time and pinned. Restated re-pulls happen at Milestone 4 as a validation step.

## 3. Data acquisition

All acquisition is scripted. Scripts live in /scripts/:

- `download_hmda.py`: fully automated against the CFPB data-browser API. Initially attempted against the legacy S3 bucket which now returns 403; pivoted to ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/csv which is the supported public endpoint.
- `download_ffiec_cdr.py`: the CDR portal is ASP.NET WebForms with VIEWSTATE-dependent postbacks. Fully scripted automation is brittle against this pattern. The script validates and registers manually-downloaded zips.
- `download_nic.py`: the NIC portal is behind Cloudflare Turnstile. Same validator-and-register pattern as CDR.

Automating form-gated portals robustly is out of scope for this project's deliverable. What matters is the manifest, not the fetch mechanism.

## 4. Schema harmonization

(To be drafted as /docs/schema-harmonization-plan.md at Milestone 2. Summary here when that lands.)

The 2018 Dodd-Frank HMDA restructure is the biggest single harmonization challenge. Pre-2018 LAR has ~40 fields keyed on (respondent_id, agency_code). Post-2018 LAR has ~110 fields keyed on LEI. Initial scope (2022 to 2024) is entirely within the post-2018 regime, so harmonization work is deferred until pre-2018 history is added.

Year-over-year drift within the post-2018 regime is handled via year-versioned seed tables in /dbt/seeds/.

## 5. Entity resolution (LEI to RSSD)

HMDA identifies lenders by LEI (post-2018). FFIEC Call Reports identify banks by RSSD. Joining them without silent-fuzzy-matching required:

- NIC institution attributes table as the authoritative crosswalk (NIC publishes LEI for banks that registered one, and RSSD is its primary key)
- FDIC BankFind Suite API for direct verification of specific institutions
- Explicit handling of non-depository lenders (no RSSD, flagged as `lender_class = independent_mortgage_company` or similar)
- SCD2 `lender_dim` table in the intermediate layer to handle merger events and form transitions

Stock Yards Bank and Trust crosswalk verified in /dbt/seeds/stock_yards_anchor_ids.csv:
- LEI: 4LJGQ9KJ9S0CP4B1FY29
- FDIC CERT: 258
- RSSD: 317342
- Louisville, KY

## 6. Data quality rules

Two layers: dbt tests and Great Expectations suites.

**dbt tests**: enforced at model-contract level. not_null on primary keys, unique on composite PKs, referential integrity on cross-source joins, custom tests for regulatory field plausibility (loan amounts in expected bands, income in expected ranges, DTI bucket values in the code list for the given year).

**Great Expectations**: row-count expectations per year, column-presence expectations per vintage, value-range expectations for key numeric fields, distribution expectations (origination rate within 45 to 55 percent nationally).

## 7. Warehouse model

(To be drafted as /docs/data-model.md at Milestone 2. Short version when that lands.)

- Staging: one table per source per grain, minimal transformation beyond type coercion and Exempt-preservation
- Intermediate: lender_dim (SCD2), date_dim, msa_dim, derived metrics per lender-year
- Marts: lender-year portfolio mart, MSA-year market mart, applicant demographic mart

## 8. Analytics: portfolio posture

(Content lands after EDA notebooks 02 and 03 execute and the dbt marts are built.)

The lender portfolio posture dashboard shows origination volume, loan-to-income distribution, denial rate, geographic concentration, and (for depositories) core capital ratio and allowance for loan loss coverage. Peer group comparisons built from Call Report asset tiers.

SYB case study: applications holding steady in the 3,400 to 4,000 range per year with a 65 percent origination rate, approximately 15 percentage points above the market baseline.

## 9. Analytics: market structure

(Content lands after EDA notebook 03.)

Top-N share, HHI, non-depository share per year nationally and per MSA for the 20 largest MSAs by origination volume. First-pass national numbers: top-10 share 21 to 22 percent, top-25 share 34 to 36 percent.

## 10. Analytics: applicant demographics

(Content lands after EDA notebook 02 and the methodology review for fair-lending disclaimers.)

Denial rate, rate spread, and average loan amount by reported race, ethnicity, sex, and income band. Every demographic view carries a prominent HMDA-limitation disclaimer.

## 11. Validation and reconciliation

(Content lands at Milestone 4.)

Three core metrics reconciled to external benchmarks:

- National origination count per year: matched against CFPB HMDA Data Browser aggregate within exact tolerance
- Top-10 lender origination counts: matched against CFPB HMDA Data Browser lender-level aggregate
- SYB total assets, tier-1 capital, and allowance for credit losses per quarter: matched against FFIEC UBPR values

Any deviation from these benchmarks is a defect and is documented in /docs/validation-report.md.

## 12. Known limitations

See /docs/known-limitations.md for the full enumeration. The load-bearing ones:

- HMDA has no credit score, no full DTI, no precise LTV (post-2018 only has buckets)
- LEI-to-RSSD crosswalk does not cover non-depository lenders
- Call Reports are restated for up to four quarters after filing
- HMDA disparity views are not determinations of discrimination; disclaimers apply

## 13. What would be different at scale

If this were a production system at a bank, not a portfolio project, these would change:

- Incremental daily loads from an internal loan origination system rather than annual public snapshots
- Row-level security for PII fields
- Real-time reconciliation to the source system rather than post-hoc reconciliation to regulator aggregates
- CRA assessment area integration with institution-specific files
- Supervisory data integrations (FFIEC Y-9C, call for stress testing)
- Dashboards scoped to internal-only users with business-unit filters

The project as built is what the public data supports with full transparency. The production extensions are noted for completeness, not claimed as in-scope.

## Reviewer notes

A reviewer looking at this repository as a portfolio piece should look at, in order:

1. /README.md for the landing page and headline findings
2. /docs/executive-summary.md for the one-page version
3. /docs/project-plan.md for the milestone structure and DoDs
4. /docs/data-quality-notes.md for the dated decision log (the real tell of whether this is disciplined work or analyst improvisation)
5. The most recent `[M{N}]` release tag for the milestone-level progression

The SYB anchor case study at notebook 04 is the smallest end-to-end demonstration that the project's value proposition works. A reviewer who reads that notebook's executed HTML has seen the core claim of the project validated against real public data.

<!-- BEGIN:eda-02-metrics -->
<!-- generated by notebooks/02-hmda-distributions-and-demographics.ipynb on 2026-04-21 -->

### Metric definitions surfaced by EDA-02

Definitions used in the EDA-02 notebook and inherited by every downstream dashboard card. Cross-reference this block before redefining any metric in M3.

- **origination rate**: count of rows with `action_taken = 1` divided by total LAR rows for the year. Denominator includes denied, withdrawn, preapproval, and purchased-loan rows.
- **denial rate**: count of rows with `action_taken = 3` divided by total LAR rows for the year. Same denominator as above.
- **originated book**: the subset `action_taken = 1`. Used for every loan-size, income, pricing, and ratio percentile in the notebook unless otherwise noted.
- **consumer book**: the subset `business_or_commercial_purpose = 2`. Excludes investor and commercial-residential loans. Used when a consumer-lending story is the point.
- **full-reporter pricing**: interest rate and rate spread percentiles computed after filtering out rows with the literal `Exempt` string in the field. Partial-exempt reporters (small lenders below HMDA full-reporting thresholds) are excluded. Any dashboard card using these metrics must disclose the filter.
- **loan amount outlier bounds**: $1 to $100,000,000. Rows outside these bounds are dropped from percentile computation. The bounds are intentionally loose. They catch fat-fingered entries without truncating legitimate jumbo activity.
- **income outlier bounds**: $1,000 to $10,000,000 annual reported income. HMDA income is in thousands of USD rounded to the nearest thousand.
- **DTI display buckets**: `<20%`, `20%-<30%`, `30%-<36%`, `36%-<50%`, `50%-60%`, `>60%`, `NA`, `Exempt`. The `36%-<50%` bucket is an analyst-facing rollup of the raw integer DTI percentages HMDA reports in that range.
- **sample-size guardrail**: 1,000 observations per cell. Applies to any demographic cross-tab. Cells below this threshold are blanked, not imputed.
- **HMDA-limitation disclaimer**: HMDA does not capture credit score, complete employment history, cash reserves, or every component of the underwriting decision. Demographic breakdowns are descriptive of the HMDA applicant population. They are not a fair-lending determination and do not establish disparate treatment.

<!-- END:eda-02-metrics -->
