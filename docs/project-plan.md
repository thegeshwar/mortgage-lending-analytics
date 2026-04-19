# Project Plan

Five milestones. Each milestone becomes a GitHub Milestone. Each deliverable becomes a GitHub Issue with a clear Definition of Done. Kanban board tracks issue flow through columns.

## Milestone 1: Discovery

Goal: problem framed, data accessed, baseline understanding documented.

Deliverables:
- [x] /docs/problem-statement.md written (who cares about this, what decision the analysis informs, what success looks like)
- [x] /docs/data-sources.md written (every source, access method, license terms, update cadence, known quirks)
- [x] HMDA LAR bulk download for at least three most recent years completed (2022, 2023, 2024 nationwide CSVs plus filer roster JSONs, manifest at data/raw/hmda/_manifest.json)
- [x] FFIEC CDR account created and Call Report bulk download completed for matching periods (12 quarters 2022Q1-2024Q4, manifest at data/raw/ffiec_cdr/_manifest.json)
- [x] /notebooks/01-initial-eda.ipynb completed (row counts per year, null patterns, distribution snapshots for action_taken, loan_type, lender size); first pass executed, findings landed in data-quality-notes.md
- [x] /docs/data-quality-notes.md started (running log of schema drift, field renames, reporter anomalies)
- [x] /docs/stakeholder-personas.md written (generic personas, no fake names, describing who would consume this work)

Definition of Done: someone unfamiliar with the project can read the discovery docs and understand what it does, why it matters, and what the data actually looks like.

## Milestone 2: Planning

Goal: architecture locked, data model designed, dashboards specified.

Deliverables:
- [ ] /docs/technical-design.md (architecture diagram, tool choices per layer, rationale for each)
- [ ] /docs/data-model.md (conceptual, logical, physical layers with ER diagrams, HMDA to FFIEC join strategy)
- [ ] /docs/data-dictionary.md (every source column and every derived column, with owner, lineage, and governance classification)
- [ ] /docs/dashboard-spec.md (every dashboard, every chart, every filter, KPI definitions, mockups)
- [ ] /docs/schema-harmonization-plan.md (cross-year HMDA schema drift reconciliation strategy)
- [ ] GitHub issues opened for every Milestone 3 build task

Definition of Done: the four design docs are detailed enough that another analyst could execute Milestone 3 without asking clarifying questions.

## Milestone 3: Build

Goal: pipeline running end to end, dashboards live, tests passing.

Deliverables:
- [ ] /dbt staging models built (raw HMDA LAR and FFIEC Call Reports to cleaned staging layer)
- [ ] /dbt intermediate models built (lender harmonization, geographic rollups, year-over-year comparables)
- [ ] /dbt marts models built (lender-year portfolio mart, MSA market mart, applicant demographic mart)
- [ ] /dbt tests passing on every model (not_null, unique, referential integrity, custom tests for regulatory field plausibility)
- [ ] /tests Great Expectations suite passing (row count expectations, value range expectations, schema expectations)
- [ ] Tableau Public dashboard published with public URL
- [ ] Power BI Service report published with public URL
- [ ] BigQuery parallel build functional
- [ ] Azure Fabric parallel build functional

Definition of Done: a cold clone of the repo, followed by the runbook, produces the same warehouse state and the same dashboards.

## Milestone 4: Validation

Goal: outputs verified against ground truth or independent calculation.

Deliverables:
- [ ] /docs/test-plan.md (every requirement mapped to every acceptance test)
- [ ] /docs/validation-report.md (results from test plan execution, including failures and remediation)
- [ ] Reconciliation of at least three core metrics against CFPB HMDA Data Browser aggregates or FFIEC published aggregates
- [ ] Lender-level spot checks against publicly known benchmarks (top 10 mortgage originators by volume)
- [ ] /docs/known-limitations.md (honest list of what this analysis cannot answer)

Definition of Done: every number on every dashboard has a documented validation path, and every known limitation is disclosed.

## Milestone 5: Publish

Goal: external-facing artifacts live, project is recruiter-ready.

Deliverables:
- [ ] /docs/methodology.md (the full writeup, publishable as a Medium or LinkedIn article)
- [ ] /docs/executive-summary.md (one page, LinkedIn Featured ready, screenshots included)
- [ ] /docs/runbook.md (how to operate the pipeline and reproduce outputs from scratch)
- [ ] Public dashboard URLs permanently referenced in README
- [ ] README updated with all external links and live screenshots
- [ ] Article draft written and scheduled for publication
- [ ] LinkedIn Featured section updated with project link

Definition of Done: a recruiter can read the README, click one link, see a live dashboard, and understand in under two minutes what was built, for whom, and what it demonstrates.

## Kanban columns

- Backlog: identified but not ready to start
- Ready: prerequisites met, available to pick up
- In Progress: actively being worked
- In Review: needs self-review, external feedback, or validation check
- Done: meets Definition of Done

## Pacing

Not committing to fake dates. Each milestone is roughly one focused weekend of work, assuming data access is in hand and tools are installed. Expect schedule drift. Record actual start and completion dates in /docs/velocity-log.md once work begins.

## GitHub setup checklist (once repo is pushed)

- [ ] Create five Milestones matching this plan
- [ ] Create a GitHub Project (v2) board with Backlog, Ready, In Progress, In Review, Done columns
- [ ] Open an Issue for each Deliverable checkbox above
- [ ] Label issues by type (docs, data, model, dashboard, test, infra)
- [ ] Pin the README and project-plan to the project home
