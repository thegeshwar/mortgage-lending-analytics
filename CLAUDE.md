# mortgage-lending-analytics

## What this project is

Portfolio analytics project on US mortgage lending data. Primary focus: consumer mortgage credit risk and lender portfolio analytics using HMDA Loan Application Register joined to FFIEC Call Report bank financials. Secondary extensions possible: fair lending disparity analysis, geographic lending coverage, peer-bank benchmarking, macro overlay with FRED indicators.

This is a self-directed portfolio project. It is not a commissioned engagement. Documentation reflects genuine analyst workflow, not fabricated corporate theater.

## Formatting rule (strict)

NO EM DASHES. Anywhere. Not in documentation, not in README files, not in code comments, not in SQL comments, not in Python docstrings, not in dashboard titles, not in commit messages, not in issue descriptions, not in pull request titles or bodies. Use hyphens, colons, commas, or parentheses instead.

This rule is absolute. Every file in this project must comply. Check before saving.

## Tone rules for documentation

Documentation should read like a genuine analyst portfolio. Specifically avoid:
- Fake exec sponsor names or approval chains
- Fabricated RACI matrices with invented role owners
- "Reviewed and signed off by [fake name] on [date]" timestamps
- Any invented organizational hierarchy

Stakeholders may be described generically as personas (for example: "credit risk officer" or "compliance analyst" or "CRA committee") without attaching fake individuals to roles.

## Stack

- Warehouse: Snowflake (primary), BigQuery and Azure Fabric (comparative parallel builds)
- Transformations: dbt Core
- Languages: Python (pandas, polars, duckdb) and SQL
- BI: Tableau Public, Power BI Service
- Data quality: dbt tests, Great Expectations
- Version control: Git and GitHub
- Project tracking: GitHub Milestones and Issues, kanban board

## Where things live

- /docs: written artifacts (problem statement, technical design, data dictionary, dashboard spec, test plan, runbook, methodology writeup)
- /data: local data working area (raw, staging, processed). Gitignored.
- /notebooks: exploratory notebooks (EDA, prototyping, ad hoc analysis)
- /sql: standalone SQL scripts for warehouse setup and manual queries
- /dbt: dbt project root (models, tests, macros, seeds)
- /dashboards: dashboard source files and exports
- /tests: Python and Great Expectations test suites
- /scripts: utility scripts for ingestion, export, setup

## Data handling

HMDA and FFIEC Call Reports are public data under each agency's redistribution terms. Raw bulk files are not committed to the repo for size reasons only, not sensitivity. Any derived datasets published to public dashboards follow source agency attribution rules.

## GitHub workflow (strict)

This project is run on GitHub the way a regulated-data engineering team would run it. No casual commits to main, no orphan work, no "I'll add the issue later". Every meaningful change is traceable from commit to PR to issue to milestone.

### The one-line rule

Nothing goes into main except through a pull request that closes a tracked issue.

### Issue-first discipline

Every unit of work begins with a GitHub Issue. If there is no issue, there is no work. The issue captures: the deliverable, the acceptance criteria (the "Definition of Done" language from the project plan), the milestone (M1 through M5), the type label (docs, data, model, dashboard, test, infra, governance), and any dependencies on other issues.

Exceptions: trivial fixes (typo in a comment, broken link in a README) may skip issue creation and go straight to a PR, but the PR body must still state what and why.

### Branch naming

Feature branches per issue. Pattern:

m{milestone}/{short-kebab-slug}-{issue-number}

Examples:
- m1/problem-statement-3
- m1/hmda-downloader-7
- m2/data-dictionary-18
- m3/stg-hmda-lar-42

Never commit directly to main. Never reuse a feature branch across issues. Once a branch is merged, it is deleted.

### Pull request requirement

Every change, including solo-authored ones, goes through a pull request. The PR is the reviewable unit of work. Self-review is still review: read your own diff as if a stranger wrote it, then merge.

PR title: [M1] brief summary (#issue-number)

PR body structure:
- What this changes (one or two sentences)
- Why it changes (link the driving decision or spec)
- Closes #issue-number (GitHub closing keyword, not optional)
- Validation performed (what you ran, what you eyeballed, what passed)
- Out of scope (explicit list of what this PR deliberately does not do)

Draft PRs are used for in-progress work that benefits from early CI feedback. Draft status is lifted only when the PR is ready for self-review merge.

### Commit messages

Small focused commits. One logical change per commit. Commit message format:

[M1] brief summary (#issue-number)

Body (optional, wrapped at 72 chars) explains why when the what is not self-evident. No em dashes. No "WIP" commits on merged branches (squash or rewrite before merge if present).

### Issue lifecycle on the project board

The GitHub Project v2 board has these columns and work moves through them in order:

- Backlog: identified but not ready to start (dependencies unmet, spec unclear)
- Ready: prerequisites met, spec clear, available to pick up
- In Progress: actively being worked, branch opened, draft PR may exist
- In Review: branch PR is out of draft, awaiting self-review or external feedback
- Done: PR merged, issue closed via closing keyword, Definition of Done met

Issues do not skip columns. An issue that cannot meet its DoD gets reopened with a followup comment describing what changed and why.

### Main branch protection

Main is the only long-lived branch. It is protected:

- Direct pushes disabled. Changes land via PR merge only.
- PR required to have a linked issue (checked in PR template).
- CI must pass before merge.
- Linear history preferred. Use squash-merge or rebase-merge; no merge commits.
- Deleted-branch-on-merge enabled repo-wide.

### CI expectations

GitHub Actions runs on every PR. At minimum:

- ruff check on all Python files
- pytest on the /tests Python suite
- dbt parse and dbt compile on the /dbt project
- Great Expectations suite dry-run where applicable
- Markdown lint (em dash detection in particular: any em dash in a changed file fails the build)

CI failures block merge. CI warnings are treated as issues to open, not noise to ignore.

### Milestone closeout

A milestone is closed only when every issue attached to it is in Done. At milestone close:

- Tag a release: v0.{milestone-number}.0, for example v0.1.0-m1-discovery
- Update README with the milestone summary and link to the release
- Cross-reference the milestone in /docs/velocity-log.md with actual start and end dates
- Open any followup issues discovered during the milestone as Backlog entries for the next milestone

### README as the living front door

README.md is treated as a landing page, not a scratch pad. It always reflects the current state of the project: current milestone, published dashboard URLs (once live), how to reproduce from a cold clone, and where to find the methodology writeup. Every merged PR that changes user-visible scope updates the README in the same PR.

### Secrets and credentials

Never committed. The repo root .gitignore excludes .env, credentials.json, profiles.yml, and related patterns. Any accidental commit of a secret triggers an immediate rotation of the credential and a history rewrite on the affected branch. Preferred secret delivery: local .env file loaded by python-dotenv, documented in README under "Local setup".

### When NOT to use GitHub issues

- Personal notes or scratch thinking: use a local working file, not a public issue.
- Half-formed ideas: let them marinate; open an issue only when the deliverable and acceptance criteria are clear.
- Vendor-tool bug reports: file upstream (dbt, Great Expectations, Snowflake connector, etc) rather than in this repo.

### Labels (standard set)

Type: docs, data, model, dashboard, test, infra, governance
Priority: p0, p1, p2
Status markers (used sparingly, board columns do most of this): blocked, needs-spec, followup
