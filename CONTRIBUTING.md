# Contributing

This is a self-directed portfolio project, but the contribution rules matter. They are how the discipline shows up in the codebase.

## The rule

Nothing goes into `main` except through a pull request that closes a tracked issue.

## Flow

1. Pick or open an issue. Confirm it has a Definition of Done, a milestone tag (M1 to M5), and a type label.
2. Create a feature branch: `m{milestone}/{short-slug}-{issue-number}`. Example: `m2/eda-01-hmda-schema-and-quality-1`.
3. Do the work in small focused commits. Format:

   ```
   [M2] brief summary (#issue-number)
   ```

4. Open a PR with this body structure:
   - What this changes (one or two sentences)
   - Why it changes (link the driving decision)
   - Closes #issue-number (required; GitHub auto-closes on merge)
   - Validation performed (commands run, outputs confirmed)
   - Out of scope (what this PR deliberately does not do)
5. Draft PRs are welcome for in-progress work. Flip to ready when you want review.
6. CI must pass: ruff, pytest, dbt parse, em-dash detector.
7. Merge with squash or rebase to keep linear history. Branch auto-deletes.
8. At milestone close, tag a release: `v0.{N}.0-m{N}-{name}`.

## Branch naming details

Feature branches per issue. Pattern:

```
m{milestone}/{short-kebab-slug}-{issue-number}
```

Examples:
- `m1/problem-statement-3`
- `m2/data-dictionary-18`
- `m3/stg-hmda-lar-42`

Never commit directly to `main`. Never reuse a feature branch across issues. Branches auto-delete on merge.

## Issue lifecycle on the project board

Issues move through these columns in order, no skipping:

- **Backlog**: identified but not ready to start (dependencies unmet, spec unclear)
- **Ready**: prerequisites met, spec clear, available to pick up
- **In Progress**: actively being worked, branch opened, draft PR may exist
- **In Review**: PR out of draft, awaiting self-review or external feedback
- **Done**: PR merged, issue closed via closing keyword, Definition of Done met

An issue that cannot meet its DoD gets reopened with a followup comment describing what changed and why.

## Main branch protection

- Direct pushes to `main` are not allowed.
- PR required to have a linked issue (checked in PR template).
- CI must pass before merge.
- Squash or rebase merge only; no merge commits.
- Deleted-branch-on-merge enabled repo-wide.

## CI expectations

GitHub Actions runs on every PR. At minimum:

- `ruff check .` on all Python files
- `pytest` on the `/tests` suite
- `dbt parse` on the `/dbt` project (skipped until dbt is initialized)
- Em-dash detector: any em dash in a changed file fails the build

CI failures block merge. CI warnings are issues to open, not noise to ignore.

## Milestone closeout

A milestone closes only when every issue attached is in Done. At close:

- Tag a release: `v0.{N}.0-m{N}-{name}`, e.g. `v0.1.0-m1-discovery`
- Update README with the milestone summary and link to the release
- Record start and end dates in `/docs/velocity-log.md`
- Open any followup issues discovered during the milestone as Backlog entries for the next milestone

## README as the living front door

`README.md` is a landing page, not a scratch pad. It always reflects the current state: current milestone, published dashboard URLs (once live), reproduction steps, methodology writeup link. Every merged PR that changes user-visible scope updates the README in the same PR.

## Secrets and credentials

Never committed. The repo root `.gitignore` excludes `.env`, `credentials.json`, `profiles.yml`, and related patterns. An accidental secret commit triggers immediate credential rotation and history rewrite on the affected branch. Preferred secret delivery: local `.env` loaded by `python-dotenv`, documented in `/docs/runbook.md`.

## Formatting rules

- **No em dashes**. Anywhere. Use hyphens, colons, commas, or parentheses. CI fails the build on any em dash in a changed file.
- No fabricated names, fake exec sign-offs, or invented RACI matrices.
- Stakeholders described as generic personas (see /docs/stakeholder-personas.md).
- Commit messages, PR titles, issue titles, code comments, SQL comments, docstrings: all subject to the no-em-dash rule.

## Commit hygiene

- One logical change per commit.
- No WIP commits on a merged branch (squash or rewrite before merge).
- Never commit secrets. `.env`, `credentials.json`, `profiles.yml` are gitignored; if one leaks, rotate the credential immediately and rewrite history.
- Never use `--no-verify` or `--no-gpg-sign`. If a hook fails, fix the hook or the underlying issue.

## Notebook style (analyst-first, narrative-driven)

Applies to every `notebooks/*.ipynb` in this repo, starting with the four-notebook EDA series defined in `/docs/eda-plan.md`. EDA notebooks are read by a human analyst seeing the dataset for the first time. They are not engineering handoffs. Structure them accordingly.

**Structure**

1. Open with a single "dataset at a glance" cell. Rows, columns, years covered, file size per vintage, one short paragraph of macro context. Not the raw manifest. Not file paths or SHA prefixes.
2. Lead with the basics a human analyst asks first in this order: row count, column count, null counts and null rates side by side, inferred data types per column per year, and **year-over-year data type drift**. These live on the first page of the notebook, not buried in later sections.
3. Only after the basics, layer in domain-specific checks (HMDA partial exemption, filer roster alignment, enum distributions, etc). Each domain section opens with one sentence of plain English on what is being checked and why.
4. Every result cell is followed by a short narrative cell: what the result shows, why it matters, what it implies for downstream modeling. Silent tables fail review.
5. Non-findings get one line. If schema delta is zero, say "no schema drift across the window" and move on. Do not print empty DataFrames.
6. Prefer one visualization over five tables for null coverage, dtype drift, or year-over-year volume. A heatmap beats a 30-row pivot.
7. Anchor case study (Stock Yards Bank and Trust) threads through every section that can carry it. Do not name-drop once and abandon.

**Language**

Section headers are plain English. Examples:

- "Can we uniquely identify a loan?" not "Composite primary key uniqueness"
- "Do all LAR lenders show up in the filer list?" not "Referential integrity against the filer roster"
- "Are the reported codes in the codebook?" not "Value-set validation on code-encoded fields"

Domain vocabulary (LEI, HMDA partial exemption, ULI, HOEPA, RSSD, MSA, DTI, LTV) stays as it is. That is the language of this dataset. Narrative cells are short, two or three sentences, lead with the observation, end with the downstream implication.

**What to strip from display tables**

Analyst-facing tables do not include `sha256`, `bytes`, `downloaded_at_utc`, `local_path`, raw SQL aliases, or per-bucket percentages when only the drift is the story. Those stay in the underlying DataFrames for helper scripts to consume.

**Generator and execution**

Notebooks are built from a generator under `scripts/build_{eda_NN}_notebook.py` so the cell sources are diff-reviewable in Python. Regenerate the `.ipynb`, then execute with `jupyter nbconvert --to notebook --execute --inplace`, then export with `--to html` to `notebooks/exports/`. Do not hand-edit the `.ipynb` JSON.

**Engineering plumbing goes in a script**

Writing to `/docs/data-dictionary.md` and `/docs/data-quality-notes.md`, writing auxiliary CSVs, or any other persistence logic belongs in a helper module under `scripts/` (convention: `scripts/eda_NN_docs.py`). The notebook invokes it in one line. The notebook shows findings. The script persists them.

**Definition of Done for an EDA notebook**

- Executes end to end against the registered data and the staging DB without error.
- HTML export exists in `notebooks/exports/`.
- Every section has narrative; every finding with a downstream implication lands in `/docs/data-quality-notes.md` with a dated entry.
- Every field-level observation lands in `/docs/data-dictionary.md`.
- Self-review confirms every section earns its place, every result has narrative, every displayed table has a reason to be there.

## Reviewing your own PR

Self-review counts. Before marking a PR ready:

- Read your own diff as if a stranger wrote it.
- Does every changed file have a reason to be touched?
- Did tests land alongside the code?
- Did the data dictionary get updated if any schema or field changed?
- Did `/docs/data-quality-notes.md` get a dated entry if a DQ decision was made?
- Is the Definition of Done from the linked issue actually met?

## Questions

Open a discussion on the repository, not on social or in private chat. Discussion threads become reference material for future work.
