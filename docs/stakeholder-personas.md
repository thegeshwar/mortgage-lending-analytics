# Stakeholder Personas

The generic personas this project's outputs are designed to serve. No invented names, no fabricated organizational hierarchy, no fake sign-off chains. These describe role archetypes, the decisions they own, what they would pull up from this project, and what they would ignore.

Four personas documented: three external consumers of the analytical outputs, and one internal persona (the project author wearing the data steward hat) whose artifacts are the real through-line of the build.

## Persona 1: Consumer credit risk analyst at a mid-size originator

### Who they are
Works in the first line of defense at a bank or independent mortgage company with meaningful mortgage origination volume. Reports up through a Chief Credit Officer or Chief Risk Officer. Their job is to monitor the posture of the origination book relative to policy, relative to stress tolerances, and relative to what peer lenders are doing.

### What decisions they inform
- Whether to tighten or loosen credit policy for a specific product segment (for example, high DTI, high LTV, jumbo, or non-owner-occupied)
- Whether the geographic concentration of recent originations is drifting into exposure they are not comfortable with
- Whether own-institution approval and denial patterns are materially different from peer lenders serving similar markets
- What to flag for the credit committee pack each quarter

### What they pull from this project
- The lender portfolio posture dashboard with own-institution preselected and a peer group selectable by asset tier, primary regulator, or geographic footprint
- Trended charts of origination mix (loan purpose, property type, occupancy, income bucket, loan amount bucket) across the past three to seven years
- Capital and allowance ratios from the Call Report side overlaid against origination volume to show whether growth has been matched by cushion
- Denial rate trend and denial reason mix as a secondary signal of underwriting stance

### What they ignore
- Fair lending pricing disparity analysis: not their lane, handed to the compliance persona
- Applicant demographic breakdowns: same reason
- Macro overlay charts beyond a quick sanity check

### What would make this dashboard credible to them
Every metric reconciled to the CFPB HMDA Data Browser or the FFIEC UBPR at the lender level, documented in the validation report. If they can reproduce a shown number using the public tools in five minutes, they will trust the rest.

## Persona 2: Fair lending and CRA compliance analyst

### Who they are
Works in second line of defense compliance, typically at a depository institution. May sit under a Chief Compliance Officer or a standalone Fair Lending group. Their job is to monitor for disparate impact and disparate treatment risk in lending, and to prepare the institution for CRA performance evaluation and for fair lending exam inquiries.

### What decisions they inform
- Which MSAs, census tracts, or applicant segments warrant targeted qualitative review
- Whether the institution's assessment area coverage is adequate and whether lending inside vs outside assessment areas is trending in a concerning direction
- What to disclose proactively to regulators when patterns suggest risk, and what to direct internal audit to investigate
- Inputs to the HMDA data integrity review that every reporter performs before submission

### What they pull from this project
- Approval rate and denial rate disparities by reported race, ethnicity, sex, and income band, with appropriate sample size guardrails
- Rate spread distributions by applicant demographic and by lender, for the segment where rate spread is reported
- MSA market structure view showing who else is lending in the same MSAs and at what approval rates, so that any own-institution outlier is visible against the market
- CRA assessment area overlay showing lending inside vs outside reported assessment areas (for depositories)

### What they ignore
- Macro overlays: not load bearing for their question
- Capital ratio views on the Call Report side

### What would make this dashboard credible to them
Explicit, prominent disclaimers about HMDA's explanatory limits. HMDA does not include credit score, fully underwritten DTI, LTV in pre-2018 vintages, or compensating factors. Disparities shown in HMDA data are not determinations of discrimination and the dashboard must say so at the top of every relevant view. Methodology must cite CFPB Fair Lending guidance explicitly.

## Persona 3: Financial regulator staff analyst or policy researcher

### Who they are
Works at a banking regulator (OCC, FDIC, Federal Reserve Board, state banking department), at CFPB, at a housing regulator (FHFA), or at an academic or think tank institution with access to the same public data but without the proprietary supervisory data. Their job is to monitor market structure, detect systemic risk signals, and produce input to policy deliberations.

### What decisions they inform
- Whether non-depository (independent mortgage company) share of origination is growing in a way that warrants policy attention
- Whether specific MSAs show unusual concentration or unusual lender churn
- Whether the rate-cycle shift in 2022 to 2023 changed the mix of who lends to whom
- Which lender segments or geographies warrant deeper supervisory review under existing authorities

### What they pull from this project
- MSA market structure views with HHI, top-5 share, and non-depository share trend
- Aggregated lender-type cuts (depository vs non-depository) with asset-size stratification on the depository side
- Peer-group comparisons built from Call Report asset tiers rather than self-reported peer lists
- Downloadable data from a public data layer so they can run their own cuts offline

### What they ignore
- Dashboard polish and aesthetic: they want data, transparent methodology, and reproducibility. Pretty charts are a bonus, not a requirement.

### What would make this dashboard credible to them
A complete methodology writeup, a downloadable aggregate data extract, and a clear statement of which HMDA snapshot vintage and which Call Report vintage the numbers were pulled from. Vintage pinning matters to this persona more than to any other.

## Persona 4: The project author, wearing the data steward hat (internal)

### Who they are
Me. The person building this. But framed here as a persona because the artifacts produced for this persona (data dictionary, lineage diagrams, data quality notes, harmonization playbook, test coverage, reconciliation records) are the actual portfolio deliverable, not a byproduct.

### What decisions this persona informs
- How a new analyst joining this codebase finds the authoritative definition of any field
- How a future version of me answers the question "why is this number different from the HMDA Data Browser" without rebuilding the reasoning from memory
- How a reviewer verifies that schema drift across HMDA 2018 was handled correctly and not papered over
- How an auditor or recruiter reading the docs determines whether the build reflects regulated-data discipline or analyst improvisation

### What this persona pulls from this project
- /docs/data-dictionary.md as the golden source of field definitions, lineage, and governance classification
- /docs/data-model.md as the authoritative statement of grain and join strategy
- /docs/schema-harmonization-plan.md as the decision record for how pre-2018 and post-2018 HMDA are reconciled
- /docs/data-quality-notes.md as the running log of anomalies and the decisions made about them
- /docs/validation-report.md as the proof that the numbers reconcile to authoritative external sources
- dbt tests and Great Expectations suites as the enforced-in-code version of the dictionary

### What this persona ignores
Nothing. This persona owns the full scope of the artifact set.

### What would make this build credible to this persona
Every claim in a dashboard traces back through the mart layer, through the intermediate layer, through staging, to a specific source file, a specific vintage, and a specific transformation step documented in dbt and in the dictionary. No orphan logic. No "I remember why we did it that way" moments. If the lineage is unclear, that is a defect to fix, not a nuance to live with.

## How the personas connect

The first three personas consume the dashboards. The fourth persona produces the governance artifacts that make the dashboards trustworthy. The connection is deliberate: dashboards without the artifact set underneath are just pictures; artifacts without dashboards are just documents. The portfolio demonstrates both, and the discipline of the fourth persona is what makes the outputs of the first three personas defensible in a regulated-data context.
