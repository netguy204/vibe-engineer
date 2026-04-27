---
discovered_by: audit batch 8c
discovered_at: 2026-04-26T02:12:33Z
severity: medium
status: open
artifacts:
  - docs/chunks/reviewer_init_templates/GOAL.md
  - src/templates/reviewers/baseline/
  - src/project.py
---

## Claim

`docs/chunks/reviewer_init_templates/GOAL.md` lists `src/templates/reviewers/baseline/DECISION_LOG.md.jinja2` in `code_paths` and references it in `code_references`:

```
- ref: src/templates/reviewers/baseline/DECISION_LOG.md.jinja2
  implements: "Baseline reviewer decision log template"
```

Success criteria #1 explicitly enumerates three required files: `METADATA.yaml.jinja2`, `PROMPT.md.jinja2`, and `DECISION_LOG.md.jinja2` — "Empty log ready for first review".

Success criteria #5 demands "Prototype alignment: Templates match the prototype content from `docs/investigations/orchestrator_quality_assurance/prototypes/reviewers/baseline/`", and the prototype directory contains `DECISION_LOG.md` alongside `METADATA.yaml` and `PROMPT.md`.

## Reality

Listing the template directory:

```
$ ls src/templates/reviewers/baseline/
METADATA.yaml.jinja2
PROMPT.md.jinja2
```

`DECISION_LOG.md.jinja2` does not exist. The implementation in `src/project.py:_init_reviewers` is candid about it:

```python
"""Initialize baseline reviewer from templates.

Creates docs/reviewers/baseline/ directory with METADATA.yaml and
PROMPT.md. Uses overwrite=False to preserve existing reviewer
configuration.
"""
```

`tests/test_project.py:TestProjectInitReviewers` only asserts that `docs/reviewers/baseline/METADATA.yaml` and `docs/reviewers/baseline/PROMPT.md` are created — `DECISION_LOG.md` is absent from the assertions. The prototype does include `DECISION_LOG.md`, so success criterion #5 is also unmet.

This is undeclared over-claim — `code_references[].status` is not flagged `partial`, but the chunk's success criteria, code_paths, and code_references all assert a `DECISION_LOG.md.jinja2` template that was never created.

## Workaround

None applied. The audit logs the discrepancy without revising the goal or implementing the missing template.

## Fix paths

1. **Add the missing template.** Create `src/templates/reviewers/baseline/DECISION_LOG.md.jinja2` matching the prototype's `DECISION_LOG.md`, extend `_init_reviewers` to render it, and add a test assertion for `docs/reviewers/baseline/DECISION_LOG.md`. This brings reality up to the chunk's stated intent and is the lowest-friction outcome — the prototype already supplies the content.
2. **Trim the chunk's claims.** Remove `DECISION_LOG.md.jinja2` from `code_paths`, `code_references`, success criterion #1, and update success criterion #5 to acknowledge METADATA + PROMPT only. This narrows the chunk to what shipped but leaves reviewer decision logging without a templated home.
