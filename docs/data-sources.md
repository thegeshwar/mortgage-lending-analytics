# Data Sources

Every source used in this project. Each entry covers: what it is, where it comes from, how it is accessed, license and attribution, update cadence, known quirks that affect modeling. This file is the authoritative reference for provenance. If a field shows up in a mart without a source documented here, that is a defect.

## HMDA Loan Application Register (LAR)

### What it is
Loan-application-level records submitted annually by covered mortgage lenders under the Home Mortgage Disclosure Act and Regulation C. Each row is one application, whether originated, approved but not accepted, denied, withdrawn, closed for incompleteness, or purchased. Fields include applicant demographics, loan characteristics, property location, action taken, denial reason, and (post-2018) pricing and underwriting disclosures.

### Source and access
- Primary publication page: ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset
- Programmatic endpoint actually used by scripts/download_hmda.py:
  - Nationwide LAR CSV: https://ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/csv?years={year}
  - Filer roster (JSON): https://ffiec.cfpb.gov/v2/reporting/filers/{year}
- Format: comma-delimited CSV (the API-served nationwide snapshot). Earlier S3 direct-download URLs are now access-controlled; the data-browser API is the supported public entry point.
- Snapshot LAR (the complete register used internally by regulators) is published after each year's edit cycle closes, typically in Q1 of year+2. This is the preferred source.
- Modified LAR (public version with certain fields redacted for privacy) is published earlier and has slightly reduced schema. Used only as a backfill if snapshot is unavailable.
- Volume: roughly 15M to 25M rows per year depending on rate environment. CSV size per year: approximately 4 GB to 6 GB uncompressed.

### License and attribution
Public data under CFPB publication terms. Redistribution permitted with attribution to CFPB and FFIEC. No royalty, no registration required. Dashboard footers and methodology docs cite "Source: FFIEC HMDA Data Publication, [year]" at minimum.

### Update cadence
- Annual, one calendar year behind. 2025 activity publishes in Q1 2027 as snapshot, earlier as modified.
- Reporter corrections and resubmissions are reflected in subsequent snapshot releases. Multiple vintages of the same report year exist; always pin to the snapshot vintage used.

### Known quirks
- **Schema drift across the 2018 Dodd-Frank restructure.** Pre-2018 LAR had roughly 40 fields; the 2018 restructure expanded to ~110 fields including rate spread, loan costs, DTI bucket, CLTV, property value, construction method, manufactured home details, applicant age, and reverse mortgage flag. Any cross-year analysis must explicitly map or stub the pre-2018 period. Handled in /docs/schema-harmonization-plan.md.
- **Minor annual edits.** Even within the 2018+ schema, bucket edges and code lists shift. Example: action_taken code list is stable but the set of valid denial reason codes has been revised. Each year's filing instructions PDF is the authoritative reference.
- **Exempt field values.** Lenders meeting partial-exemption criteria under the 2018 HMDA rule can report "Exempt" in place of certain fields. Must be handled explicitly: null imputation is wrong; the exempt status is itself meaningful.
- **Lender identifier transition.** Pre-2018 lenders identified by (respondent_id, agency_code). 2018 forward uses Legal Entity Identifier (LEI), a 20-char alphanumeric assigned by GLEIF-accredited LOUs. Joining pre- and post-2018 history on a single lender requires the respondent panel crosswalk (see below).
- **Reporter panel turnover.** Merged, acquired, or dissolved institutions continue to appear under their legacy LEI for several years of reporting. Must be reconciled against NIC institution event history for point-in-time peer grouping.
- **Code-encoded fields.** action_taken, loan_type, loan_purpose, occupancy_type, and applicant demographic fields are integer codes. Code lookups are documented in the FFIEC filing instructions and will be seeded in /dbt/seeds as reference tables.
- **Geography granularity.** Property location is reported at the state, county, and census tract level. MSA is derivable from county via the OMB delineation (which itself drifts across releases and must be version-pinned).

### Primary key and grain
No natural single-field primary key in the raw file. Composite candidate: (LEI, activity_year, loan_application_number) where loan_application_number is the lender-assigned ULI (universal loan identifier) post-2018 or the NULI (non-universal loan identifier) for exempt reporters. Pre-2018 used a different composite. Uniqueness is asserted in staging tests and violators are logged rather than silently deduplicated.

## FFIEC Call Reports

### What it is
Consolidated Report of Condition and Income filed quarterly by every FDIC-insured commercial bank and savings institution. Balance sheet, income statement, loan portfolio composition, capital ratios, liquidity, derivatives, and operational data. The financial picture of the lender side of the HMDA story.

### Source and access
- Primary: FFIEC Central Data Repository Public Data Distribution, cdr.ffiec.gov/public
- Format: SDF (pipe-delimited text) bulk download per report period per form type
- Volume: approximately 4,000 to 5,000 active filers per quarter (declining as consolidation continues)

### Form variants
- **FFIEC 031**: banks with foreign offices. Largest institutions. Fullest schedule set.
- **FFIEC 041**: domestic-only institutions above ~$5B in assets. Most mid-size banks.
- **FFIEC 051**: streamlined form for small banks under ~$5B, fewer schedules, reduced item count.

All three forms must be unioned for full peer-universe coverage. Schedule and field alignment across forms is documented in the FFIEC MDRM (Micro Data Reference Manual).

### License and attribution
Public under FFIEC terms. No restriction on redistribution. Attribution standard: "Source: FFIEC Call Reports, [period]".

### Update cadence
- Quarterly, filed within 30 days of quarter end (large banks) or 35 days (small banks).
- Restatements are common for up to four quarters after original filing. Pulling "as filed" vs "as of" vintage matters: trend charts must use a consistent vintage policy documented in data-quality-notes.md.

### Known quirks
- **MDRM code evolution.** Schedule items are identified by MDRM codes (e.g. RCFD2170 for total assets). Some codes are stable for decades; others are renamed, split, or retired. Notable recent case: allowance for loan and lease losses (ALLL) was retired in favor of allowance for credit losses (ACL) under CECL adoption around 2020. Historical continuity requires mapping retired codes to their successors.
- **Form transitions.** A bank crossing the $5B threshold moves from FFIEC 051 to FFIEC 041. New schedules appear; some items that existed on 051 map to different cells on 041. Must be handled in the staging layer.
- **Merger accounting.** When bank A acquires bank B, bank B's RSSD continues to exist historically but ceases reporting. Bank A's subsequent reports absorb B's book. Point-in-time peer comparisons must respect this: comparing pre-merger bank A to post-merger bank A without adjustment is misleading.
- **Restated quarters.** The CDR distributes the most recent vintage by default. Historical analysis comparing "as filed" to later restatement values requires the vintage-specific download.
- **RSSD identifier.** Primary key for the filer. Assigned by the Federal Reserve System. Stable across the institution's life until merger or charter change. Cross-referenced with FDIC certificate number, OCC charter number, and (where registered) LEI in the NIC institution reference file.

### Grain and primary key
(RSSD, report_period, form_type) is the composite primary key. Staging asserts uniqueness.

## NIC Institution Reference Data

### What it is
National Information Center institutional data, maintained by the Federal Reserve. The authoritative crosswalk for bank identifiers: RSSD, FDIC certificate, OCC charter, LEI (where reported), parent holding company relationships, charter class, regulator assignment, opening and closing events.

### Source and access
- Primary: ffiec.gov/npw/FinancialReport/ReturnDataPortal and FFIEC bulk data files at ffiec.gov/npw/Help/FinancialData
- Attributes bulk download: institution snapshot CSV with current and historical institution records
- Relationships bulk download: parent-subsidiary-affiliate graph with effective dates

### Why this source matters
This is the connective tissue between HMDA (LEI-keyed) and Call Reports (RSSD-keyed) for banks. For any HMDA-reporting bank with an LEI, NIC gives the RSSD. The crosswalk is maintained by the regulator and is authoritative. It is not derived via fuzzy name matching, which would be a defect given the authoritative source exists.

### License and attribution
Public. Attribution: "Source: FFIEC National Information Center".

### Update cadence
NIC is updated continuously as institutional events are recorded. Bulk files are refreshed periodically (weekly for relationships, snapshot-based for attributes). For a reproducible build, pin the download date.

### Known quirks
- **Not all HMDA lenders have an RSSD.** Independent mortgage companies, credit unions outside the FFIEC-reporting perimeter, and some fintech originators report HMDA but do not file Call Reports. They are a distinct lender class in the data model and carry a null RSSD throughout the warehouse.
- **LEI registration is voluntary for smaller institutions.** An NIC record without an LEI means that institution cannot be joined to HMDA via LEI. For such cases, fallback to respondent panel crosswalk if the institution appears in HMDA's pre-2018 history.

## HMDA Transmittal Sheet and Reporter Panel

### What it is
FFIEC publishes the roster of HMDA filers per year with identifying attributes (LEI, agency code, respondent ID, institution name, address, tax ID). The Transmittal Sheet is the filing cover record; the Reporter Panel is the pre-2018 crosswalk between (respondent_id, agency_code) and institution attributes.

### Source and access
- Primary: ffiec.cfpb.gov/data-publication/panel-data
- Format: pipe-delimited per year

### Why this source matters
For pre-2018 HMDA history, the reporter panel is the bridge from legacy (respondent_id, agency_code) to institution identity, which can then be crosswalked to LEI (for the 2018+ years when the same institution filed) or to RSSD via NIC.

## GLEIF LEI Registry (secondary)

### What it is
Global Legal Entity Identifier Foundation public registry. Each LEI record includes the legal name, registered address, entity legal form, registration status, and corporate relationship data.

### Source and access
- Primary: gleif.org/en/lei-data/gleif-concatenated-file
- Format: full file (XML or JSON) of all issued LEIs, refreshed daily
- In this project: consulted only when NIC crosswalk is insufficient (e.g. non-bank HMDA lender with no NIC record but a registered LEI)

### License and attribution
Public, CC0 license. No attribution required but provided as a courtesy.

## FRED Macro Series (optional overlay)

### What it is
Federal Reserve Economic Data published by the Federal Reserve Bank of St. Louis. Macro time series used to contextualize the lender-level story.

### Source and access
- Primary: FRED API, fred.stlouisfed.org/docs/api
- API key required (free)
- Series of interest:
  - MORTGAGE30US: 30-year fixed mortgage rate, weekly
  - UNRATE: unemployment rate, monthly
  - CSUSHPISA: S&P Case-Shiller national home price index, monthly
  - CPIAUCSL: CPI all urban, monthly
  - DGS10: 10-year Treasury constant maturity, daily

### License and attribution
FRED API terms, attribution required: "Source: Federal Reserve Bank of St. Louis, FRED".

### Update cadence
Varies by series. Pull cadence in this project: monthly refresh of all subscribed series with vintage pinning.

## OMB CBSA / MSA Delineation

### What it is
Office of Management and Budget Core-Based Statistical Area and Metropolitan Statistical Area delineation. Maps counties (FIPS) to MSAs.

### Source and access
- Primary: census.gov/programs-surveys/metro-micro/about/delineation-files.html
- Format: Excel and CSV per delineation vintage

### Why this source matters
HMDA reports county FIPS and (in some vintages) MSA code, but the county-to-MSA mapping drifts across OMB delineation releases. To produce a consistent MSA grain across years, pin a single delineation vintage per analysis run and document which was used.

### License and attribution
Public. Attribution: "Source: US Office of Management and Budget CBSA delineation, [vintage]".

## Summary of cross-source joins used

| From | To | Via | Notes |
|------|-----|-----|-------|
| HMDA LAR (2018+) | Bank Call Report | LEI -> NIC -> RSSD | Authoritative crosswalk, not fuzzy match |
| HMDA LAR (pre-2018) | Bank Call Report | (respondent_id, agency_code) -> Reporter Panel -> LEI -> NIC -> RSSD | Multi-hop, some loss expected |
| HMDA LAR | MSA rollup | county_fips -> OMB CBSA | Pinned delineation vintage |
| Call Report | peer group | RSSD -> asset-size bucket | Derived, documented in data dictionary |
| HMDA or Call Report | macro overlay | activity_year or report_period -> FRED series period | Period alignment rules documented |

## What is explicitly not a source

- Proprietary lender data. Not used, not referenced, not invoked as anecdote. All content in this project is derivable from the public sources listed above.
- Credit bureau data. Not available under any public license at the granularity needed. HMDA's underwriting limitations (no credit score, no full DTI, no LTV in pre-2018) are accepted constraints and are documented in /docs/known-limitations.md.
- Any scraped, synthesized, or internally-generated "insider" lender performance data. The honest scope of this project is what the public sources permit.
