# Known Limitations

Honest list of what this analysis cannot answer and why. An analyst portfolio piece that pretends these limits do not exist is not credible. Recruiters, peers, and domain reviewers spot overreach quickly.

This file is maintained alongside the project. Every limitation here traces to either (a) a structural property of the public data or (b) a conscious scope decision documented in /docs/data-quality-notes.md. Items are added as they surface.

## What HMDA data does not contain

**Credit scores**. HMDA applications do not report FICO, VantageScore, or any credit score. Analyses of approval or denial patterns in HMDA cannot control for credit history, which is one of the most load-bearing underwriting factors. Any disparity shown in this project's dashboards is not a determination of discrimination; it is a descriptive statistic with an explicit missing-variable disclaimer.

**Full debt-to-income detail**. HMDA 2018+ reports DTI as a bucket, not an exact value. Pre-2018 data has no DTI at all. Bucket cutpoints have been adjusted across filing years, so cross-year DTI cuts require the year-specific lookup tables documented in /docs/data-quality-notes.md.

**Loan-to-value precision**. HMDA 2018+ reports CLTV as a bucket. Property value is reported for most loans but with its own set of reporting exemptions. Pre-2018 LAR has no LTV at all.

**Compensating factors**. Underwriters consider cash reserves, income stability, employment history, payment history, and collateral condition in ways that do not surface in HMDA. A denied application in HMDA may have been denied for a perfectly legitimate compensating-factor reason that the data simply does not capture.

**Pre-application steering**. HMDA captures applications that were submitted. It cannot see the universe of potential applicants who were steered away before formal application, or who walked away after an informal conversation with a loan officer.

**Loan performance after origination**. HMDA is an application register. It does not track whether loans subsequently defaulted, were refinanced, were sold to the secondary market under what terms, or were subject to loss mitigation.

## What the LEI-to-RSSD crosswalk cannot resolve

**Independent mortgage companies**. Non-depository mortgage lenders (IMCs) report HMDA but do not file FFIEC Call Reports. They have no RSSD. In 2024 they represent a material share of HMDA origination volume. Analyses that pair HMDA origination to Call Report balance sheet metrics are depository-only. The IMC segment is treated as a distinct lender class with a null RSSD throughout this project.

**Smaller credit unions**. Many credit unions report HMDA but file with NCUA rather than FFIEC. Their structural data is in NCUA's Credit Union Online call report system, not in the Call Reports pulled here. Treated as a separate lender class similar to IMCs.

**Smaller banks without LEI**. LEI registration is voluntary for smaller institutions. An FFIEC Call Report filer without an LEI cannot be joined to HMDA by the regulator-maintained crosswalk. In practice this set is small and its HMDA volume is minimal, but the gap is noted.

**Pre-2018 HMDA history**. HMDA used (respondent_id, agency_code) as the lender key before the 2018 Dodd-Frank restructure. Joining pre-2018 LAR to a post-2018 LEI-keyed world requires a multi-hop bridge (Reporter Panel to LEI, then LEI to RSSD via NIC) with some loss at each hop. This project restricts its initial scope to 2022 forward, so the pre-2018 gap is not active; future extensions would need to reconcile it.

## What the FFIEC Call Reports do not show

**Off-balance-sheet exposures in full detail**. Call Reports include Schedule RC-L for off-balance-sheet items, but some commitments, guarantees, and credit enhancements are reported at higher levels of aggregation than the balance sheet's on-book items.

**Intra-quarter timing**. Call Report snapshots are period-end. A bank that added and removed a large loan position mid-quarter might look identical at period-end to one that never touched it.

**Subsidiary-level detail for holding companies**. Call Reports are filed per bank RSSD. A large holding company's consolidated FR Y-9C filing has richer detail but is a different data set not pulled here.

**As-filed vs restated**. Call Reports are restated for up to four quarters after original filing. This project pulls the latest-available vintage at download time. Historical reanalysis using as-filed vintage requires a separate vintage-specific pull.

## What this project's scope explicitly excludes

**Modeling, prediction, or scoring**. No regression, classification, or clustering beyond basic descriptive statistics. The project is a descriptive portfolio analytics build, not a predictive or prescriptive exercise.

**Legal or regulatory opinion**. Nothing in this repository is a legal determination. Disparities shown in HMDA data are not adjudications of discrimination. Capital ratio views on the Call Report side are not assessments of supervisory concern.

**Proprietary or insider data**. No non-public data is used. The project's honesty anchor is that every number shown can be reproduced from the public sources listed in /docs/data-sources.md.

**Dashboard access control**. Dashboards publish publicly via Tableau Public and Power BI Service. There is no internal-only view, no row-level security, no user-specific filters. A regulator, a compliance analyst, and an interested member of the public see the same dashboard.

## What a future extension could add

These are not commitments. They are scope ideas that would be honest extensions if time permits.

- Macro overlay with FRED rate, unemployment, and HPI series
- Pre-2018 HMDA back-history with the Reporter Panel bridge
- Peer groups constructed from NIC holding-company structure instead of flat asset tiers
- CRA assessment area overlay (requires the institution-specific assessment area files)
- Fair-lending regression specifications (for discussion and methodology, not adjudication)

Each of these would open a GitHub Issue at the time of scoping, with its own DoD and limitations section update.
