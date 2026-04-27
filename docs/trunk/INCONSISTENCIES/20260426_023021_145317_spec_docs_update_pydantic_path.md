---
discovered_by: audit batch 10f
discovered_at: 2026-04-26T02:30:21
severity: low
status: open
artifacts:
  - docs/chunks/spec_docs_update/GOAL.md
---

## Claim

`docs/chunks/spec_docs_update/GOAL.md` line 45 (Consistency success criterion):

> Frontmatter schema in SPEC.md matches the actual Pydantic models in `src/ve/subsystems.py`

## Reality

The path `src/ve/subsystems.py` does not exist. The actual subsystem Pydantic models live at `src/subsystems.py` (top-level, not under `src/ve/`). There is no `src/ve/` package in the repo at all.

```
$ ls src/ve/
ls: src/ve/: No such file or directory

$ ls src/subsystems.py
src/subsystems.py
```

The success criterion is otherwise satisfied — SPEC.md's documented frontmatter schema does match the Pydantic models in `src/subsystems.py`. Only the path reference is wrong.

## Workaround

None required. The criterion is functionally met against the correct path; only the path string is stale.

## Fix paths

1. **Update GOAL.md to name the correct path** — change `src/ve/subsystems.py` to `src/subsystems.py`. Mechanical fix; preserves intent.
2. Restructure the codebase to actually live under `src/ve/` (very out-of-scope).

Preferred: option 1, in a follow-up cleanup chunk. The audit refrains from rewriting success-criterion text per the audit's "success criteria are off-limits" rule.
