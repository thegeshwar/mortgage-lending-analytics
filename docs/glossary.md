# Glossary

Acronyms and domain terms used across this project. Organized alphabetically. Entries carry enough context to be useful to a reader who has not spent a decade in bank regulatory data.

## A

**ACL**: Allowance for Credit Losses. Reserve a bank holds against expected loan losses, measured under the CECL accounting standard (effective staggered adoption around 2020). Replaced ALLL in Call Report schedules. MDRM codes changed accordingly.

**ALLL**: Allowance for Loan and Lease Losses. The pre-CECL predecessor concept to ACL. Retired in Call Reports at each institution's CECL adoption date. Historical time series must map retired MDRMs to their successors.

**Anchor reporter**: in this project, Stock Yards Bank and Trust Company (LEI 4LJGQ9KJ9S0CP4B1FY29). The lender used as the concrete case study throughout the EDA and dashboards.

**Application (HMDA)**: a mortgage loan application meeting HMDA reporting thresholds. Each row in HMDA LAR is one application, whether originated, denied, withdrawn, purchased, or otherwise disposed.

## B

**BankFind Suite**: FDIC API for institution metadata. banks.data.fdic.gov. Used in this project to verify the LEI-to-RSSD mapping for specific institutions.

## C

**CBSA**: Core-Based Statistical Area. OMB-maintained groupings of counties into metropolitan and micropolitan statistical areas. The delineation is revised periodically; this project pins a single vintage per analysis run.

**CDR**: Central Data Repository, the FFIEC system through which banks file Call Reports. The public data distribution at cdr.ffiec.gov is how bulk Call Report data is obtained.

**CECL**: Current Expected Credit Losses. Accounting standard (ASC 326) that replaced the incurred-loss model for loan-loss reserves. Adopted by banks at staggered dates around 2020.

**CERT**: FDIC Certificate number. Unique identifier assigned by FDIC to insured depository institutions. Primary key for FDIC BankFind. Stock Yards CERT = 258.

**CFPB**: Consumer Financial Protection Bureau. Regulator that administers HMDA. Publishes the HMDA LAR through ffiec.cfpb.gov.

**Code-encoded field (HMDA)**: a HMDA field whose values are integer codes that must be joined to a filing-instructions lookup (for example action_taken where 1 = originated, 3 = denied). Code lists can shift across years.

**CRA**: Community Reinvestment Act. Requires banks to demonstrate meeting credit needs of the communities (assessment areas) where they take deposits. HMDA data is a key input to CRA performance evaluations.

## D

**dbt**: data build tool. Core transformation framework in this project's stack. Compiles SQL templated models with references, tests, and documentation.

**DoD**: Definition of Done. Stated at the bottom of each milestone in /docs/project-plan.md. An issue is closed only when its DoD is met.

**Dodd-Frank (HMDA 2018)**: Dodd-Frank Wall Street Reform Act of 2010 required a substantial expansion of HMDA reporting that took effect in 2018. HMDA LAR schema expanded from roughly 40 fields to roughly 110 fields including rate spread, loan costs, DTI bucket, LTV bucket, and applicant age.

**DTI**: Debt-to-Income ratio. Applicant's total monthly debt divided by monthly income. Reported in HMDA 2018+ as a bucket, not an exact value.

## E

**EOCD**: End-of-Central-Directory record. Structural marker at the tail of a zip file identifying where the central directory lives. A zip without EOCD is considered truncated. Relevant here because some NIC CSV zips arrived truncated in the initial fetch and required raw deflate-stream recovery.

**Exempt (HMDA)**: the literal string "Exempt" reported in certain HMDA fields by lenders meeting partial-exemption criteria under the 2018 rule. Preserved as a distinct category in this project's staging layer rather than null-imputed.

## F

**FDIC**: Federal Deposit Insurance Corporation. Insures deposits and regulates state-chartered banks not members of the Federal Reserve. Publishes BankFind Suite API.

**FFIEC**: Federal Financial Institutions Examination Council. Coordinates the federal bank regulators (FRS, FDIC, OCC, NCUA, CFPB). Administers Call Reports and publishes HMDA.

**FFIEC 031, 041, 051**: the three active Call Report forms. 031 for banks with foreign offices, 041 for mid-size domestic-only banks, 051 for small banks under about $5B. Schedules overlap but are not identical.

**FRED**: Federal Reserve Economic Data. Macro time series published by the Federal Reserve Bank of St. Louis. Optional overlay in this project for rate environment and macro context.

## G

**GLEIF**: Global Legal Entity Identifier Foundation. Maintains the authoritative registry of LEIs. Referenced in this project as a fallback crosswalk source when NIC lacks a record.

## H

**HHI**: Herfindahl-Hirschman Index. Sum of squared market shares, used to measure concentration. Reported in this project's MSA market structure dashboard.

**HMDA**: Home Mortgage Disclosure Act. Requires covered mortgage lenders to report application-level data annually. Administered by CFPB. The HMDA LAR is the primary data asset in this project.

**HMDA LAR**: Loan Application Register. The per-application record set submitted by HMDA reporters each year. Published in Snapshot (full, post-edit-cycle) and Modified (privacy-redacted, earlier release) variants.

## I

**IMC**: Independent Mortgage Company. Non-depository mortgage lender that reports HMDA but does not file FFIEC Call Reports (no RSSD). A distinct lender class in this project's data model.

## K

**Kanban**: the status-flow board used for this project's issues. Columns: Backlog, Ready, In Progress, In Review, Done. Every issue moves through them in order.

## L

**LEI**: Legal Entity Identifier. 20-character alphanumeric identifier issued by GLEIF-accredited Local Operating Units. Used by HMDA starting 2018 as the lender identifier. Stock Yards LEI = 4LJGQ9KJ9S0CP4B1FY29.

**LTV**: Loan-to-Value ratio. Loan amount divided by property value. Reported in HMDA 2018+ as a bucket.

## M

**Manifest**: sha256-hashed inventory file at data/raw/{source}/_manifest.json that records every downloaded asset's URL, size, checksum, and acquisition timestamp. The record of truth for vintage pinning.

**MDRM**: Micro Data Reference Manual. FFIEC's dictionary of Call Report line-item codes (e.g. RCFD2170 for total assets). Codes are stable-ish but some are retired or split across schedules over time.

**Modified LAR (HMDA)**: public HMDA release with selected fields redacted for privacy, published earlier than the Snapshot. This project uses Snapshot exclusively.

**MSA**: Metropolitan Statistical Area. OMB designation grouping counties around a core urban area. Derivable from HMDA's county FIPS via the CBSA delineation.

## N

**NCUA**: National Credit Union Administration. Regulates federally insured credit unions. Not a HMDA regulator per se, but credit unions that meet HMDA thresholds still report.

**NIC**: National Information Center. Federal Reserve System's authoritative repository of banking institution structure data. Publishes bulk downloads at ffiec.gov/npw. The source of this project's LEI-to-RSSD crosswalk.

## O

**OCC**: Office of the Comptroller of the Currency. Regulator of national banks and federal savings associations. Assigns OCC charter numbers.

**OMB**: Office of Management and Budget. Maintains the CBSA delineation used to map counties to MSAs.

**Origination (HMDA action_taken = 1)**: the mortgage application resulted in a loan being made. The key dependent variable for most analyses in this project.

## P

**PK (primary key)**: unique identifier for a table row. In this project's staging, the HMDA LAR composite PK is (lei, activity_year, universal_loan_identifier); the Call Report composite PK is (rssd, report_period, form_type).

## R

**Rate spread (HMDA)**: the difference in percentage points between an originated loan's APR and the average prime offer rate (APOR) for a comparable loan. Reported when the spread exceeds a threshold, indicating higher-cost lending.

**RC, RI (Call Report schedules)**: Schedule RC is the consolidated balance sheet. Schedule RI is the income statement. Sub-schedules (RC-A, RC-C, RC-K, RI-A, etc.) break out specific line items. Every Call Report zip in this project unpacks into 51 schedule files.

**Reporter panel (HMDA)**: the roster of all HMDA filers for a given year with identifying attributes. Published by FFIEC alongside the LAR. Pre-2018 vintages use (respondent_id, agency_code) as the key; 2018+ uses LEI.

**RSSD**: Federal Reserve identifier for a depository institution. Assigned by the Federal Reserve System. Stable across an institution's life until merger or charter change. Stock Yards RSSD = 317342.

## S

**SCD2**: Slowly Changing Dimension Type 2. Dimension-table modeling pattern that preserves history by adding effective_from / effective_to date columns to each row. Used for this project's lender_dim to handle merger events.

**Schedule (Call Report)**: subset of Call Report line items grouped by topic (balance sheet, income statement, securities, deposits, loans, derivatives, etc.). Each zip contains 51 schedule TXT files per period.

**Snapshot LAR (HMDA)**: the full HMDA register published after each year's edit cycle closes, typically in Q1 of year+2. Preferred vintage for this project.

## T

**Taxonomy (Call Report)**: the XBRL schema for a given Call Report form. Downloadable from cdr.ffiec.gov via the "Download Taxonomy" button.

**Transmittal Sheet (HMDA)**: the cover record filed with each year's HMDA submission, containing filer identifying attributes.

## U

**UBPR**: Uniform Bank Performance Report. FFIEC-published peer-group ratios derived from Call Report data. Used in this project as a reconciliation benchmark at Milestone 4.

**ULI**: Universal Loan Identifier. Unique loan-level identifier introduced in HMDA 2018+. Part of the LAR composite primary key.

## V

**Vintage (data vintage)**: the specific version of a published dataset corresponding to a given download date. FFIEC Call Reports are restated for up to four quarters after original filing, so vintage pinning matters. Recorded in each manifest entry as downloaded_at_utc.

**VIEWSTATE**: ASP.NET WebForms mechanism for preserving server-side control state across postbacks. Relevant here because the FFIEC CDR form uses WebForms and the VIEWSTATE has to be round-tripped correctly when automating form submissions.
