<!-- PR title format: [M{N}] brief summary (#issue-number) -->

## What this changes

<!-- One or two sentences. Direct. -->

## Why

<!-- Link the driving spec, issue, or data-quality decision. No em dashes. -->

## Closes

<!-- Required. GitHub auto-closes the linked issue on merge. -->
Closes #

## Validation performed

<!-- Commands run, outputs eyeballed. Specifics only. -->
- [ ] `ruff check .` passes
- [ ] `pytest` passes (if tests touched or added)
- [ ] `dbt parse` passes (if dbt touched)
- [ ] Em-dash detector: zero hits on changed files
- [ ] Data-quality-notes.md updated if a DQ decision was made
- [ ] Data-dictionary.md updated if a schema or field changed
- [ ] Relevant notebook regenerated and HTML export committed (if notebook touched)

## Out of scope

<!-- What this PR deliberately does not do. Protects against scope creep. -->
