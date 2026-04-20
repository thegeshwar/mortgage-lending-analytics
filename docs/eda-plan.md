# Initial Full EDA Plan

Scope of the exploratory data analysis for Milestone 1 closure and Milestone 2 design input. This document is the spec for what the notebooks will produce, the questions each notebook answers, and the artifacts each notebook emits. The earlier /notebooks/01-initial-eda.ipynb was a scratch pass and has been archived under /notebooks/archive/. This plan defines the real deliverable.

## Guiding principles

0. **Analyst-first narrative.** Every notebook is written for a human analyst seeing the dataset for the first time. Lead with what an analyst asks first: row counts, column counts, null counts and rates, inferred dtypes, and year-over-year dtype drift. Only then layer in domain-specific checks. Every result has a short narrative cell after it that says what it shows, why it matters, and what it implies for downstream. Section headers are plain English, not database jargon. Full style rules live in /CONTRIBUTING.md under "Notebook style."
1. Every number reported anywhere in the EDA is reproducible from the raw zips registered in the manifests at data/raw/{hmda,ffiec_cdr,nic}/_manifest.json. No one-off queries, no unsaved cell outputs.
2. Every finding that affects downstream modeling gets written into /docs/data-quality-notes.md with a date stamp and a decision statement. Engineering plumbing (writing those files) lives in helper scripts under /scripts/, not inside the notebook.
3. Every notebook exports both the executed .ipynb and an HTML render to /notebooks/exports/ so a reviewer can read findings without running anything.
4. No em dashes anywhere. No fabricated context. SYB is the anchor case study because it is a real HMDA filer with known characteristics, not as a rhetorical device. Once invoked in a notebook, it threads through every section that can carry it.
5. Stock Yards Bank and Trust anchor IDs pinned in /dbt/seeds/stock_yards_anchor_ids.csv: LEI 4LJGQ9KJ9S0CP4B1FY29, FDIC CERT 258, RSSD 317342, Louisville KY.

## Notebook series

Four notebooks. Each stands alone with its own imports and data access. Runtime target: each notebook under 10 minutes end to end on the local machine against the registered data.

### 01: HMDA Schema and Quality EDA

Goal: answer the first-look questions an analyst has about the HMDA LAR across 2022, 2023, 2024. What are we holding, what is in it, where is it missing, where is it inconsistent, and what does that imply for every notebook that runs after.

Sections (analyst-first order, plain-English headers):

1. **Dataset at a glance.** Rows per year, column count per year, file size per vintage, one short paragraph of macro context (the 2022 to 2024 window spans the post-COVID rate shock). Verified row counts: 16,099,307 (2022) / 11,564,178 (2023) / 12,229,298 (2024).
2. **Is the schema stable across years?** Column-presence matrix, year-over-year delta. A single line if there is no drift, a table if there is.
3. **What kinds of values live in each column, and do they drift over time?** Per-column inferred type (int, float, exempt, text, mixed) for each of 2022, 2023, 2024. Side-by-side drift pivot that shows, for example, that `loan_to_value_ratio` moved from 0 percent integer-formatted values in 2022 to roughly 15 percent in 2024. Narrative distinguishes "mixed because HMDA uses `Exempt`/`NA`/`1111` sentinels by design" from "mixed because lender reporting practice is drifting year over year."
4. **Where is the data actually missing?** Null count and null rate side by side per column per year. Structural multi-slot tails (applicant_race-5, applicant_ethnicity-4, aus-5, etc) are expected and called out as such. The interesting nulls are the 20 to 30 percent null pricing fields (lender_credits, discount_points) and anchor fields with non-trivial null rates.
5. **How much of the reporter panel is on partial exemption?** Distinct reporters with at least one Exempt value per year (first pass: 1,354 / 1,996 / 2,021 LEIs). Plain-English callout that this is roughly 41 percent of the 2024 panel, and that any pricing-field analysis has to segment full vs partial reporters or systematically under-sample them.
6. **At what grain is this data, and is the reporter panel stable?** ULI absence across all three vintages, mean rows per LEI, distinct LEI count per year. Observation: 2023 had more reporters than 2022 despite 28 percent less volume. That is the rate-shock signature and informs lender segmentation in notebook 03.
7. **Do the lenders in the LAR all show up in the filer roster?** Symmetric-difference on LEI sets per year. Orphan-in-LAR (filed without registration) vs orphan-in-roster (registered but did not file). Name any LEI in the orphan-in-LAR set, since those rows will join-null to lender attributes downstream. SYB sanity check that weaves in: SYB volume trajectory (3,982 / 3,498 / 3,447 records) against the national 24 percent volume drop.
8. **Are the reported codes in the codebook, and do the distributions tell us anything?** Enum-field distributions per year for action_taken, loan_type, loan_purpose, occupancy_type, construction_method, business_or_commercial_purpose, hoepa_status, lien_status, preapproval. Any value not documented in the 2022 to 2024 HMDA filing instructions is a defect. The distribution itself is the analyst finding: origination rate through the rate shock, HOEPA high-cost loan volume year over year, loan_purpose=5 ("other") trajectory.
9. **Findings to carry forward.** One-per-line plain-English list mapping each finding to the notebook or dbt model it constrains downstream.

Artifacts:
- /notebooks/exports/01-hmda-schema-and-quality.html
- /docs/data-dictionary.md updates written via `scripts/eda_01_docs.py` (field-level type, nullability, code-list references)
- /docs/data-quality-notes.md dated entry written via `scripts/eda_01_docs.py` (every finding with a downstream decision implication)

### 02: HMDA Distributions and Demographics

Goal: understand the shape of HMDA application activity across the key univariate and bivariate dimensions.

Sections:
1. action_taken distribution per year (verified first pass: origination rate 52.2, 49.4, 50.5 percent; denial rate 15.5 to 17.6 percent).
2. loan_type and loan_purpose mix, conditional on action_taken = 1 (originated). Cross-tabs per year.
3. occupancy_type, construction_method, property_type breakdowns.
4. business_or_commercial_purpose share (originations that are not primarily residential).
5. Loan amount distribution: mean, median, p25, p75, p95 by year and by loan_purpose. Outlier flags (loans above 99th percentile and below 1st percentile).
6. Income distribution with the same statistics, bucketed for readability.
7. Rate spread and interest rate distributions conditional on originated loans where the value is reported (not null, not Exempt).
8. DTI ratio and LTV ratio bucket distributions.
9. Applicant demographic profile: derived_race, derived_ethnicity, derived_sex distributions per year. Joint vs individual applicant mix.
10. Applicant age bucket distribution (introduced in HMDA 2018+).
11. Denial reason mix conditional on action_taken = 3. Cross-tab denial reason by derived demographics with sample-size guardrails (at least 1,000 applications per cell before reporting).

Artifacts:
- /notebooks/exports/02-hmda-distributions-and-demographics.html
- /docs/methodology.md drafts for any metric that will surface on a dashboard

### 03: Lender and Market Structure

Goal: characterize the lender panel and the market structure on the HMDA side, independent of the Call Report side.

Sections:
1. Lender count per year (verified: 4,454 / 5,093 / 4,878). Investigation of the 2023 spike and 2024 decline.
2. Top 10, top 25, top 50, top 100 origination-share per year. HHI per year nationally.
3. Lender-class segmentation: depository (will be resolvable via NIC RSSD linkage) vs non-depository (no RSSD match). Interim segmentation by name-pattern heuristic until the crosswalk is wired.
4. MSA-level market structure for the 20 largest MSAs by origination volume. Top-5 share and HHI per MSA per year.
5. Geographic coverage. State-level origination volume, originations-per-100k population overlay, and a list of states with unusually sparse coverage relative to population.
6. Lender quality variance. Flag LEIs with: null rate on any anchor field above 50 percent, origination rate outside 20 to 80 percent band (market baseline 50 percent), average loan amount more than 3 standard deviations from segment mean.
7. Reporter panel turnover: LEIs present only in 2022 (exited), only in 2024 (entered), across all three years (stable). Table of counts and implied share of volume.
8. SYB case study cuts. For LEI 4LJGQ9KJ9S0CP4B1FY29 in each year: total applications, origination rate, loan-purpose mix, geographic footprint at the MSA level, denial rate, share of HMDA volume nationally and in Louisville MSA. Verified baseline: roughly 3,500 applications per year, origination rate stable at 65 percent (approximately 15 percentage points above market).

Artifacts:
- /notebooks/exports/03-lender-and-market-structure.html
- /docs/data-dictionary.md updates for derived lender-dim fields

### 04: FFIEC Call Reports Profile plus HMDA-to-Call-Report Join Feasibility

Goal: understand the Call Report side, then verify the LEI-to-RSSD crosswalk works end to end.

Sections:
1. Call Report vintage inventory. 12 quarterly zips registered for 2022Q1 through 2024Q4. File sizes per quarter (verified: 5.8 MB to 6.9 MB range). TXT file inventory per zip (51 files per period, one per schedule plus POR).
2. Reporter panel per quarter. Distinct RSSDs per form variant (FFIEC 031, 041, 051). Union distinct count.
3. Form-variant transitions. RSSDs that appear on different forms across the 12 quarters (e.g. 051 to 041 when crossing the asset threshold). Flagged for continuity handling.
4. Core metrics spot check. For 10 large bank RSSDs with stable form assignment: total assets trend, tier 1 capital trend, allowance for credit losses trend across 12 periods. Sanity check against FFIEC UBPR published aggregates.
5. NIC institution reference unpack. Confirm LEI column present in attributes (verified: col 72 = ID_LEI in CSV_ATTRIBUTES_ACTIVE). Count of active institutions with populated LEI. Count without.
6. LEI-to-RSSD join coverage. Across the 2024 HMDA filer panel (roughly 4,925 LEIs), how many resolve to an RSSD via the NIC crosswalk? Document the unmatched set by name and expected lender class (independent mortgage company, credit union, etc).
7. SYB case study end to end. Resolve LEI 4LJGQ9KJ9S0CP4B1FY29 to RSSD 317342 via NIC. Pull SYB total assets, tier 1 capital, allowance for credit losses, and quarterly residential mortgage loan outstanding across 2022Q1 to 2024Q4. Pair with SYB HMDA origination volume per year. First readable lender-year time series that crosses both datasets.
8. Non-depository handling. Confirm that a sample of known independent mortgage companies (top 5 IMCs by 2024 HMDA volume) have no RSSD match and no Call Report filings. Document handling plan in /docs/data-quality-notes.md.

Artifacts:
- /notebooks/exports/04-callreport-profile-and-join-feasibility.html
- /docs/data-dictionary.md updates for Call Report schedules, MDRM codes, and joined lender-year metrics
- /docs/data-quality-notes.md updates documenting any unmatched lenders or MDRM surprises

## Execution order and gating

1. Notebook 01 runs first. Its output is the prerequisite for notebooks 02 and 03.
2. Notebooks 02 and 03 can run in parallel after 01 completes.
3. Notebook 04 runs last because it depends on the NIC crosswalk being validated and on SYB's HMDA cuts from notebook 03.

Each notebook emits a "Findings for data-quality-notes.md" markdown block at the bottom that can be copy-pasted directly into /docs/data-quality-notes.md.

## Dashboard-facing outputs (not in EDA scope, for M2 design)

Not produced by the EDA. The EDA surfaces the inputs that the M3 dashboard build will use.

Three dashboards, as specified in /docs/problem-statement.md:
1. Lender portfolio posture (SYB anchor, peer-group selectable)
2. MSA market structure (top 20 MSAs, any year)
3. Applicant demographic lens (fair lending cut, with HMDA-limitation disclaimer)

The EDA must have validated every underlying input dataset before the dashboard spec (/docs/dashboard-spec.md at M2) is written.

## Definition of Done for the initial full EDA

- All four notebooks execute end to end against the registered raw data without errors
- Each notebook has a saved HTML export in /notebooks/exports/
- /docs/data-dictionary.md has a field-level entry for every HMDA LAR column and every Call Report schedule referenced in the notebooks
- /docs/data-quality-notes.md has a dated entry for every decision the EDA forced
- The SYB end-to-end case study (notebook 04 section 7) produces a lender-year time series that pairs HMDA origination volume with Call Report balance-sheet figures. This is the smallest demonstration of the project's value proposition working end to end.

## What this EDA is explicitly not

- Not a modeling exercise. No regressions, no predictive scoring, no feature engineering beyond basic univariate and bivariate statistics.
- Not a fair lending determination. Demographic breakdowns carry the standard HMDA-limitation disclaimer at the top of any output that shows them.
- Not a dashboard build. Dashboard work is Milestone 3.
- Not a regulatory-opinion document. Descriptive statistics on public data, with disciplined documentation of every decision.
