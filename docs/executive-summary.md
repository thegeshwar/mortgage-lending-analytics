# Executive Summary

One page. Written so a reviewer who has ninety seconds gets the point. Updated as the project progresses.

## Project

`mortgage-lending-analytics`: a portfolio analytics build on public US mortgage lending data. HMDA Loan Application Register joined to FFIEC Call Report bank financials, anchored on Stock Yards Bank and Trust Company (Louisville, KY, LEI 4LJGQ9KJ9S0CP4B1FY29).

## The question the project answers

Which US mortgage lenders are extending the most credit risk relative to the financial cushion they are carrying, and how has that posture shifted year over year across geographies and borrower segments?

Origination volume alone is not risk. A lender that tripled originations while tripling tier-1 capital is not in the same position as a lender that tripled originations on a flat capital base. This distinction is reconstructable from public data and is what the project makes visible.

## What this demonstrates

The project is built as a data-steward portfolio piece, not just an analytics build. The artifacts under the dashboards are the point:

1. Complete data dictionary with lineage and governance classification for every source and derived column
2. Schema harmonization playbook covering the 2018 Dodd-Frank HMDA restructure and annual code-list drift
3. LEI-to-RSSD crosswalk using the regulator-maintained NIC institution reference (not fuzzy name matching)
4. Dated data-quality log for every decision that shaped the output
5. Reconciliation to CFPB HMDA Data Browser and FFIEC UBPR aggregates

## Scale

- 39.9 million HMDA applications across 2022, 2023, 2024
- 12 quarters of FFIEC Call Reports covering every FDIC-insured commercial bank and savings institution
- 5 NIC institution reference files plus the full LEI registry as fallback
- 15 GB of raw data, sha256-manifested for vintage pinning

## Headline findings

- US mortgage origination volume dropped 28 percent from 2022 to 2023 as the rate cycle compressed, then recovered 6 percent in 2024
- Market origination rate (applications that become loans) is stable at 50 to 52 percent across years
- Top-10 lender market share is only 21 to 22 percent: the US mortgage market is materially more diffuse than the "big five banks" narrative assumes
- Stock Yards Bank and Trust origination rate holds steady at 65 percent, roughly 15 percentage points above the market baseline, a cleanly observable pattern consistent with a qualified-applicant mid-size regional bank book
- Exempt-value reporting under the 2018 HMDA partial-exemption rule is consistently 2.33 percent across every eligible field, implying a fixed cohort of small reporters, and is preserved as a distinct category rather than null-imputed

## Stack

Snowflake, dbt Core, Tableau Public, Power BI Service, Python (duckdb, polars, pandas), Git, GitHub Actions. BigQuery and Azure Fabric built in parallel as portability demonstrations.

## Dashboards

Three dashboards, published at Milestone 3. Live links pinned in README when available.

1. Lender portfolio posture (own-institution vs peer group)
2. MSA market structure (top 20 metros)
3. Applicant demographic lens (fair-lending cut with HMDA-limitation disclaimers)

## What this is not

Not a predictive model. Not a fair-lending legal determination. Not a regulatory-opinion document. Not a claim of proprietary insight beyond what the public data supports. Known limitations enumerated in /docs/known-limitations.md.

## Status

Milestone 1 (Discovery) closed 2026-04-19. Milestone 2 (Planning) in progress with 10 tracked issues. Full project plan at /docs/project-plan.md.

## Contact

Thegeshwar Sivamoorthy. Self-directed portfolio project. Repository: https://github.com/thegeshwar/mortgage-lending-analytics.
