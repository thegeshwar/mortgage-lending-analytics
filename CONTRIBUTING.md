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
