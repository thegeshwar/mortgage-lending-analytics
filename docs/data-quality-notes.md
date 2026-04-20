# Data Quality Notes

Running log of data-quality observations, decisions, and open issues for the HMDA and FFIEC data in this project. Each entry is dated and cross-referenced to the GitHub Issue that tracks resolution. This file is intentionally not a polished doc: it is the working record that feeds the dictionary, the harmonization plan, and the validation report.

Format for new entries:

```
## YYYY-MM-DD [source] short title (#issue)
Observation: what was seen.
Impact: what downstream work is affected.
Decision: what we do about it. Provisional decisions marked [provisional].
Owner: self (data steward hat).
```

## Vintage pinning decisions

### 2026-04-19 [HMDA] Snapshot vintage, not modified LAR (#pending)
Observation: HMDA is published in two vintages, Snapshot (full register after edit cycle) and Modified LAR (subset with privacy redactions, published earlier). Snapshot has complete schema; Modified drops selected fields.
Impact: the entire analytical surface depends on schema completeness, especially rate_spread and property_value.
Decision: use Snapshot LAR as the exclusive source for years 2022, 2023, 2024 (the three most recent vintages available as of project start). Modified LAR is not loaded. Manifest (data/raw/hmda/_manifest.json) records the download timestamp for each year's Snapshot zip as the vintage pin.
Owner: self.

### 2026-04-19 [FFIEC CDR] As-filed vs restated policy (#pending)
Observation: FFIEC restates Call Report data for up to four quarters after initial filing. CDR's bulk download returns the most recent vintage by default.
Impact: comparisons across periods can be inconsistent if one period is "fresh" and another is "matured". Peer group metrics can shift if a large filer restates.
Decision [provisional]: pull the latest-available vintage for every period included in the analysis and record the download timestamp. Historical reanalysis will use the same vintage snapshot. A second-pass load with "as-filed" vintage is a Milestone 4 validation step, not a Milestone 3 build dependency.
Owner: self.

## Schema drift and field-level anomalies

### 2026-04-19 [HMDA] 2018 Dodd-Frank schema restructure (#pending)
Observation: HMDA LAR schema changed materially in the 2018 reporting year. Pre-2018: approximately 40 fields. Post-2018: approximately 110 fields including rate_spread, loan_costs, DTI bucket, CLTV bucket, property_value, construction_method, manufactured_home_details, applicant_age, and reverse_mortgage flag.
Impact: cross-year analysis that spans 2017 and earlier requires explicit schema harmonization. The 2022 to 2024 initial scope is entirely within the post-2018 regime, so this drift is a Milestone 2 concern not an M1 blocker.
Decision: document full field-level mapping in /docs/schema-harmonization-plan.md when written at M2. For M1 EDA, restrict to 2018 forward.
Owner: self.

### 2026-04-19 [HMDA] Exempt field values (#pending)
Observation: lenders qualifying for partial exemption under the 2018 HMDA rule may report the literal string "Exempt" in certain fields instead of a value. This applies to a subset of fields including (but not limited to) loan costs, origination charges, discount points, lender credits, interest rate, prepayment penalty term, DTI ratio, CLTV, and introductory rate period.
Impact: these fields are typed as numeric downstream but arrive as mixed-type strings. Null-imputing "Exempt" destroys information: the exempt status is itself meaningful for segmentation.
Decision: preserve "Exempt" as a distinct category through staging. In the marts layer, expose both the numeric value (null when exempt) and an is_exempt_for_field boolean. Code this into the dictionary and the dbt staging model contracts.
Owner: self.

### 2026-04-19 [HMDA] Code list changes year over year (#pending)
Observation: even within the 2018+ schema, code lists for fields like denial_reason and action_taken have been adjusted across annual filing instructions. Bucket edges for loan_to_value_ratio and debt_to_income_ratio have also shifted in places.
Impact: a value that appears in year X may not have existed in year Y. Downstream aggregations that pivot by code value must handle the "new in year Z" case.
Decision: seed each year's filing instructions code tables into /dbt/seeds as year-versioned reference tables (code_list_{field}__{year}). Staging joins to the correct year's lookup.
Owner: self.

### 2026-04-19 [HMDA] Reporter panel turnover and LEI continuity (#pending)
Observation: merged, acquired, or dissolved institutions continue to appear under their legacy LEI for several years. The Reporter Panel and NIC institution event history are the authoritative sources for stitching LEIs into a point-in-time institutional identity.
Impact: peer grouping, own-institution trend lines, and lender concentration metrics need LEI-to-entity resolution with an effective-date layer. A simple LEI group-by is misleading post-merger.
Decision: model a lender_dim SCD2 in the intermediate layer keyed on LEI with effective_from / effective_to windows sourced from NIC. All peer and concentration logic joins to this dim, not to raw LEI.
Owner: self.

## Cross-source joins

### 2026-04-19 [HMDA+FFIEC] LEI to RSSD crosswalk source (#pending)
Observation: HMDA identifies lenders by LEI (post-2018). FFIEC Call Reports identify banks by RSSD. No direct LEI column in the Call Report files.
Impact: without a reliable crosswalk, the whole lender-balance-sheet side of the project does not land.
Decision: use NIC institution attributes as the authoritative LEI-to-RSSD crosswalk (NIC publishes LEI for banks that registered one). This is a regulator-maintained match, not a fuzzy name match. Where NIC lacks an LEI for a Call Report filer, fall back to name-and-address inspection and document each fallback match individually; do not silently fuzzy-match.
Owner: self.

### 2026-04-19 [HMDA] Non-depository lenders have no RSSD (#pending)
Observation: independent mortgage companies, many credit unions outside the FFIEC reporting perimeter, and certain fintech originators report HMDA but do not file Call Reports.
Impact: any HMDA analysis joined to Call Report is silently biased to depositories unless non-depositories are explicitly tracked as a distinct class.
Decision: lender_dim carries a lender_class attribute: bank, credit_union, independent_mortgage_company, other. Non-depositories are kept in-scope for HMDA-side analysis with a null RSSD and an explicit lender_class value. Dashboards show depository vs non-depository cuts as a first-class filter.
Owner: self.

## Pre-2018 history (not yet in scope)

### 2026-04-19 [HMDA] respondent_id and agency_code to LEI bridging (#pending)
Observation: pre-2018 HMDA used (respondent_id, agency_code) as the lender key. The 2017-and-earlier years require a bridge to the 2018+ LEI world to produce a continuous history.
Impact: any analysis extending before 2018 needs the Reporter Panel bridge.
Decision [provisional]: out of scope for M1 initial load (2022 to 2024 only). When the history extension is scoped, document the bridge in schema-harmonization-plan.md and add a pre-2018 staging track.
Owner: self.

## FFIEC Call Report specifics

### 2026-04-19 [FFIEC CDR] Form variant union (#pending)
Observation: the three active Call Report forms (FFIEC 031, 041, 051) have overlapping but not identical schedules and MDRM coverage. A bank's form assignment depends on asset size and foreign-office presence and can change over time.
Impact: a bank that crosses the FFIEC 051 to FFIEC 041 threshold appears with different schedules before and after. Time series for that bank fractures at the boundary if forms are handled independently.
Decision: stage each form separately in staging, then union into a single intermediate model keyed on (rssd, report_period) with schedule availability flags. The dictionary tracks which MDRM codes are available from which forms.
Owner: self.

### 2026-04-19 [FFIEC CDR] ALLL to ACL MDRM transition under CECL (#pending)
Observation: allowance for loan and lease losses (ALLL) concept was replaced by allowance for credit losses (ACL) under CECL adoption at staggered dates across the industry. MDRM codes changed accordingly.
Impact: a continuous "reserves" time series requires mapping the retired MDRM to the successor, with an institution-specific adoption date.
Decision: maintain a mdrm_history reference seed documenting retirement date, successor code, and transition notes. The intermediate model applies the institution's adoption date to select the correct code per period.
Owner: self.

### 2026-04-19 [FFIEC CDR] Merger accounting continuity (#pending)
Observation: when bank A acquires bank B, bank B's RSSD stops reporting and bank A's subsequent filings absorb B's book. Pre-merger A to post-merger A is not a like-for-like series.
Impact: lender_year time series on the Call Report side can show sharp jumps that are accounting, not operating.
Decision: flag merger events in the lender_dim SCD2 with a breakpoint attribute. Trend charts on dashboards respect the breakpoint (either show the discontinuity or show a combined-pro-forma series with an explicit caveat). The decision of which to show is dashboard-level and spec'd in /docs/dashboard-spec.md.
Owner: self.

## Geography

### 2026-04-19 [HMDA] OMB CBSA delineation vintage (#pending)
Observation: HMDA reports property at state, county, and census tract level. The county-to-MSA (CBSA) mapping is maintained by OMB and revised periodically. Different HMDA reporting years implicitly reference different delineations.
Impact: rolling up a multi-year series to MSA grain with the wrong delineation silently miscounts any county whose CBSA assignment changed.
Decision: pin a single OMB CBSA delineation vintage per analysis run. Document which vintage was used in the dashboard methodology footer. The pin lives in /dbt/seeds as cbsa_delineation_{vintage}.
Owner: self.

## Reconciliation targets

### 2026-04-19 [HMDA] CFPB HMDA Data Browser as reconciliation benchmark (#pending)
Observation: the CFPB HMDA Data Browser (ffiec.cfpb.gov/data-browser) publishes aggregate views of the same underlying data used in this project. Any lender-year or market total shown on this project's dashboards must reconcile to a corresponding Data Browser aggregate within a documented tolerance.
Impact: if a number in this project's dashboard does not match Data Browser, that is a defect.
Decision: /docs/validation-report.md at M4 enumerates specific reconciliation checks: top 10 lenders by origination count per year, MSA totals for the 10 largest MSAs by population, denial rate by state. Tolerance: exact match on counts, within 0.1 percentage point on rates.
Owner: self.

## First data-touch observations

### 2026-04-19 [HMDA] Stock Yards Bank and Trust LEI confirmed (#pending)
Observation: the filer roster (ffiec.cfpb.gov/v2/reporting/filers/{year}) returns Stock Yards Bank and Trust Company under LEI 4LJGQ9KJ9S0CP4B1FY29 in 2022, 2023, and 2024, unchanged across the three years.
Impact: the SYB anchor-case LEI is stable across the initial load window. No merger-induced LEI change to reconcile for this reporter in scope.
Decision: pin this LEI as the canonical SYB identifier in the lender_dim seed. Any subsequent vintage that does not return this LEI for SYB triggers a manual investigation before the load proceeds.
Owner: self.

### 2026-04-19 [HMDA+FFIEC] Stock Yards full identifier crosswalk (#pending)
Observation: FDIC BankFind Suite API confirms Stock Yards Bank and Trust Company (Louisville, KY) under FDIC CERT 258 and FED_RSSD 317342. An unrelated "Stock Yards Bank and Trust Company" in Austin, Indiana (RSSD 1847, CERT 21645) is inactive and should not be confused with the Louisville entity.
Impact: the crosswalk LEI 4LJGQ9KJ9S0CP4B1FY29 to RSSD 317342 is directly verified rather than inferred. A naive name-based match would surface both entities.
Decision: captured in /dbt/seeds/stock_yards_anchor_ids.csv as a first-class seed. Any LEI-to-RSSD logic that resolves to a non-Louisville Stock Yards row is a defect.
Owner: self.

### 2026-04-19 [HMDA] Filer panel size drop 2023 to 2024 (#pending)
Observation: HMDA reporter panel sizes from the v2 filers API: 2022 = 4,483 institutions, 2023 = 5,134 institutions, 2024 = 4,925 institutions. A net decrease of 209 filers from 2023 to 2024.
Impact: peer-group and market-concentration calculations depend on a consistent universe. A shrinking panel can reflect reporting-threshold crossings, merger attrition, or institution exits, and each mechanism has different analytical meaning.
Decision: do not treat the panel size as interchangeable across years. Intermediate models should carry an activity_year attribute on lender_dim and resolve peer groups year by year. Full reconciliation of the 2023-to-2024 delta (threshold crossings vs mergers vs exits) is deferred to the NIC event-history integration at Milestone 2.
Owner: self.

### 2026-04-19 [HMDA] Bulk S3 snapshot URLs are no longer publicly listed (#pending)
Observation: prior CFPB publication paths at s3.amazonaws.com/cfpb-hmda-public/prod/snapshot-data/... now return HTTP 403. The public data-browser API at ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/csv is the working entry point.
Impact: any older documentation, blog post, or tutorial linking to the S3 paths is stale. Vintage pinning and reproducibility depend on capturing the response from the data-browser API at download time, not on the S3 paths.
Decision: scripts/download_hmda.py uses the data-browser API exclusively. The manifest records the full API URL per download so a reproducer knows exactly which endpoint was called.
Owner: self.

## First EDA pass findings (2026-04-19)

### Row counts per activity year
- 2022: 16,099,307 rows
- 2023: 11,564,178 rows (28.2% decline vs 2022, consistent with the rate-cycle compression)
- 2024: 12,229,298 rows (5.8% recovery vs 2023)

### action_taken distribution
Origination rate (code 1) is remarkably stable across the three years: 52.2% in 2022, 49.4% in 2023, 50.5% in 2024. Denial rate (code 3) held at 15.5% to 17.6%. Purchased-loan rows (code 6) ran at 9.7% to 10.9%, indicating the secondary-market reporter presence is a first-class concern for any "origination volume" metric (must filter to code 1).

### Lender concentration
Panel sizes by year: 4,454 / 5,093 / 4,878 (the 2023 peak appears to reflect threshold-driven reporter additions that then thinned in 2024). Top-10 share of originations sits at 20.8% to 22.3% and top-25 at 33.8% to 36.1%. This is materially more diffuse than commonly assumed and supports a peer-group analysis approach rather than a "five giant banks" narrative.

### Stock Yards Bank and Trust case study baseline
- 2022: 3,982 applications (origination rate 64.6%)
- 2023: 3,498 applications (origination rate 64.7%)
- 2024: 3,447 applications (origination rate 65.4%)

SYB's origination rate sits roughly 15 percentage points above the market average (about 50%), consistent with a mid-size regional lender that underwrites a qualified-applicant book rather than a volume-at-all-costs book. This is a cleanly observable pattern in the raw data that the portfolio analysis can build on.

### Exempt-value reporting prevalence (2024)
Across interest_rate, rate_spread, origination_charges, debt_to_income_ratio, and loan_to_value_ratio, the Exempt value appears in exactly the same ~285,000-row range per field (2.33% of total). The consistent count strongly suggests a fixed cohort of partial-exemption reporters is responsible. Confirms the /docs/data-quality-notes.md earlier decision to preserve Exempt as a distinct category through staging rather than null-impute.

### Field-name correction logged
Initial exempt-field probe assumed loan_costs as the column name; actual field is total_loan_costs. The HMDA data dictionary uses the total_ prefix for aggregated origination-cost fields. Noted for the field-naming layer of /docs/data-dictionary.md.

## Open items without decisions yet

- Whether to include the HMDA Transmittal Sheet and Reporter Panel as first-class sources or load them lazily on demand.
- Whether to stand up a vintage-archive of both HMDA and Call Report downloads for historical reproducibility, or treat the first download as the pin for this project's lifetime.
- How to surface non-bank credit union reporting in NIC (some credit unions are tracked, many are not) without double-counting or gapping.
- Whether the rate_spread reporting guardrails (reporting threshold above APOR) warrant a separate is_higher_priced dimension in the marts layer.

Each of these will open as a GitHub Issue when the question is forced by downstream work.

<!-- BEGIN:eda-01-2026-04-19 -->
## 2026-04-19 | EDA-01 HMDA Schema and Quality

Row counts verified per year: 2022 = 16,099,307, 2023 = 11,564,178, 2024 = 12,229,298.

Column surface union across 2022 to 2024: 99 columns. Columns absent from at least one year: 0.

Mixed-type columns flagged: 21. These require explicit cast rules in staging. See notebook section 3.

Universal Loan Identifier absent from nationwide public LAR in all three years. Decision: downstream loan-grain models must either accept a synthesized row-ordinal key or switch source to the LAR release that preserves ULI.

Exempt-value reporters per year: 2022 = 1,354 LEIs, 2023 = 1,996 LEIs, 2024 = 2,021 LEIs.

Undocumented code-field values found: 0. See notebook section 8 for the full table.

<!-- END:eda-01-2026-04-19 -->

<!-- BEGIN:eda-01-2026-04-20 -->
## 2026-04-20 | EDA-01 HMDA Schema and Quality (analyst-first revision)

### Dataset shape
Row counts: 2022 = 16,099,307, 2023 = 11,564,178, 2024 = 12,229,298. A 28% drop from 2022 to 2023, soft +5.8% recovery into 2024. This is the post-COVID rate-shock signature and the macro context every downstream HMDA notebook operates within.

Schema: 99 columns across all three years. Columns absent from any year: 0. The 2018 HMDA schema is stable across this window.

### Data type drift (reporting practice, not schema change)
Several pricing fields show lenders shifting from decimal-formatted reporting to integer-formatted reporting over the three vintages. Downstream models must cast these consistently or year-over-year comparability silently degrades.

| Column | 2022 int% | 2024 int% | Delta |
| --- | --- | --- | --- |
| `tract_to_msa_income_percentage` | 4.6 | 100.0 | +95.4 pp |
| `loan_to_value_ratio` | 0.0 | 14.8 | +14.8 pp |
| `origination_charges` | 0.0 | 9.4 | +9.4 pp |
| `lender_credits` | 0.0 | 3.2 | +3.2 pp |
| `discount_points` | 0.0 | 2.7 | +2.7 pp |
| `total_loan_costs` | 0.0 | 2.4 | +2.4 pp |
| `interest_rate` | 0.0 | 1.9 | +1.9 pp |
| `applicant_age` | 10.3 | 11.9 | +1.6 pp |
| `income` | 88.7 | 85.5 | +-3.2 pp |

Mixed-type columns flagged in at least one year: 21. Most of these are mixed by design (HMDA uses `Exempt`, `NA`, `1111`/`8888`/`9999` sentinels for not-applicable values). The drift table above isolates the subset where lender reporting practice changed year over year.

### Non-structural null fields worth watching

| Column | 2022 null rate | 2023 null rate | 2024 null rate |
| --- | --- | --- | --- |
| `lender_credits` | 29.77% | 29.95% | 30.21% |
| `discount_points` | 21.11% | 18.75% | 20.08% |

Structural multi-slot fields (applicant_race-5, aus-5, etc) exceeding 99% null are expected and excluded from this list.

### Partial-exemption panel
Distinct reporters using at least one `Exempt` value per year: 2022 = 1,354 LEIs, 2023 = 1,996 LEIs, 2024 = 2,021 LEIs. The 2022 to 2023 jump (+47%) is a structural shift in how many small reporters exercise partial exemption, likely driven by the rate-shock volume collapse dropping more lenders below the full-reporting threshold. Any pricing analysis downstream must segment full vs partial reporters.

### Reporter grain and panel churn
ULI absent in all three vintages. Panel: 2022 = 4,480 LEIs across 16,099,307 rows, 2023 = 5,129 LEIs across 11,564,178 rows, 2024 = 4,908 LEIs across 12,229,298 rows. 2023 added 649 LEIs despite 28% less origination volume than 2022, meaning smaller average books per lender. Refi specialists exited, niche/portfolio lenders persisted or entered. Decision: downstream loan-grain models cannot rely on a natural PK from the nationwide LAR. Use a synthetic row-ordinal key or switch source to the LAR release that preserves ULI.

### Filer-roster alignment

| Year | Roster LEIs | LAR LEIs | Orphan in LAR | Orphan in roster |
| --- | --- | --- | --- | --- |
| 2022 | 4,483 | 4,480 | 1 | 4 |
| 2023 | 5,134 | 5,129 | 1 | 6 |
| 2024 | 4,925 | 4,908 | 0 | 17 |

Orphan-in-LAR LEIs (filed without registration) by year: 2022: 549300SBCJXCPODZN187; 2023: 254900FR7KYE3QFAIX50; 2024: none. These will join-null to any lender attribute (asset size, charter type) downstream unless handled explicitly.

SYB (LEI 4LJGQ9KJ9S0CP4B1FY29) records per year: 2022 = 3,982, 2023 = 3,498, 2024 = 3,447. SYB volume dropped roughly 13% across the window vs the national 24% drop. The anchor case held up better than the market.

### Enum distributions and anomalies
Undocumented enum values found across 9 code-encoded fields: 0. Observed distribution shifts worth carrying forward: origination rate 52.2/49.4/50.5 percent; HOEPA high-cost loans 8,477/11,114/6,426 (-42% 2023->2024); loan_purpose=5 72,299/55,454/20,446 (-72% across window).

<!-- END:eda-01-2026-04-20 -->
