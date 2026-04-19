# Problem Statement

## The question this project answers

Which US mortgage lenders are extending the most credit risk relative to the financial cushion they are carrying, and how has that posture shifted year over year across geographies and borrower segments?

Mortgage origination volume alone is not risk. A lender that tripled originations while simultaneously tripling tier 1 capital is not in the same position as a lender that tripled originations on a flat capital base. A lender booking high loan-to-income originations in one MSA is not in the same position as one with a diversified geographic footprint. These distinctions matter, and they are reconstructable from public data.

## Who would care about the answer

Three analyst personas, described generically. See /docs/stakeholder-personas.md for the full writeup.

- A consumer credit risk analyst at a bank or non-bank originator, benchmarking own-institution posture against peer lenders
- A fair lending or CRA compliance analyst looking for outliers in approval, pricing, and geographic coverage patterns
- A financial regulator staff analyst or policy researcher monitoring systemic concentration and underwriting drift

None of these personas needs a proprietary data feed to do this work. They need the public data, cleaned, harmonized across schema years, and joined to the lender balance sheet side. That is the gap this project fills.

## Why this is worth building

HMDA Loan Application Register is released annually with reporter-level granularity. FFIEC Call Reports publish bank financials quarterly. Each has been used independently for decades. The join between them, reporter ID on one side to RSSD on the other, is doable but nontrivial: schema drift across HMDA years, reporter panel turnover, non-depository lenders that appear in HMDA but not in Call Reports at all. Most published analysis either stays on one side of the join or aggregates away the lender-level detail that makes the join useful. A portfolio-level cut that respects both the origination side and the capital side is the contribution.

## What success looks like

Three dashboards, each answering a specific question:

1. Lender portfolio posture. For any selected lender-year, show origination volume, loan-to-income distribution, denial rate, geographic concentration, and (where applicable) core capital ratio and allowance for loan loss coverage. Peer group comparison built in.

2. MSA market structure. For any selected MSA-year, show lender concentration (top 5 share, HHI), approval rate distribution across lenders, and demographic composition of applicants versus originations.

3. Applicant demographic lens. For any selected year and geography, show denial rate, rate spread, and average loan amount cuts by reported race, ethnicity, sex, and income band, with sample-size guardrails and appropriate disclaimers about HMDA's explanatory limitations.

Every number on every dashboard reconciles to an independent source (CFPB HMDA Data Browser aggregates, FFIEC published aggregates, or hand calculation from the raw files). Reconciliation documented in /docs/validation-report.md at Milestone 4.

## What this project is not

This is not a credit scoring model. It is not a fair lending legal determination. It is not an endorsement of any lender or policy position. It is a descriptive portfolio analytics build on public data, with transparent methodology and documented limitations.

HMDA data does not include credit scores, debt-to-income ratios that account for all obligations, loan-to-value details, or other underwriting variables that would be needed to draw causal conclusions about lending decisions. /docs/known-limitations.md at Milestone 4 will enumerate these limits explicitly.

## Decision this informs

For a credit risk persona: whether own-institution posture is drifting toward higher-risk origination patterns relative to peer group, and whether that drift is compensated by capital or reserves.

For a compliance persona: which MSAs and which applicant segments warrant deeper qualitative review under fair lending or CRA frameworks, flagged by outlier status against peer and market baselines.

For a regulator or researcher persona: where market concentration is rising, where non-depository share is growing, and which macro overlays (interest rate, unemployment, house price) correlate with underwriting shifts.

The dashboards do not make the decision. They surface the pattern that prompts the conversation.

## Artifacts this produces

The dashboards are the visible surface. The artifacts underneath are the point.

- /docs/data-dictionary.md covering every source column and every derived column, with lineage, owner, governance classification, and authoritative definition
- /docs/data-model.md with conceptual, logical, and physical layers plus entity resolution strategy (LEI to RSSD, respondent panel to LEI for pre-2018 history)
- /docs/schema-harmonization-plan.md documenting HMDA schema drift reconciliation across the 2018 Dodd-Frank restructure and the smaller year-over-year edits since
- /docs/data-quality-notes.md as a running log of reporter anomalies, edit flag patterns, correction resubmission behavior, and exempt-field handling decisions
- /docs/validation-report.md reconciling every dashboard number to an authoritative source (CFPB HMDA Data Browser aggregates, FFIEC published aggregates, or hand calculation)
- Data flow diagrams from source files through landing, staging, intermediate, and marts layers
- dbt tests and Great Expectations suites enforcing the dictionary definitions in code

These are the deliverables a data steward produces when standing up regulated data in a warehouse. The fact that they happen to also be what a portfolio analytics build needs is not a coincidence.
