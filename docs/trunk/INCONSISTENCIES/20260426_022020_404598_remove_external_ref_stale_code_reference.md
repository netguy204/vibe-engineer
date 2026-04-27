---
discovered_by: audit batch 9e
discovered_at: 2026-04-26T02:20:20Z
severity: low
status: open
artifacts:
  - docs/chunks/remove_external_ref/GOAL.md
---

## Claim

`docs/chunks/remove_external_ref/GOAL.md` lists in `code_references`:

```yaml
- ref: src/ve.py#remove_external
  implements: "CLI command ve artifact remove-external"
```

## Reality

`src/ve.py` no longer defines a `remove_external` symbol — `grep -n "remove" src/ve.py` returns nothing. The command moved to `src/cli/artifact.py#remove_external` during the CLI modularization (the same chunk's frontmatter already includes the correct successor reference at `src/cli/artifact.py#remove_external`, with `implements: "CLI artifact remove-external command after CLI modularization"`).

The stale entry is therefore a duplicate of an already-corrected reference. Both entries point to the same logical command, but only the `src/cli/artifact.py` one is true.

## Workaround

None needed at runtime — the chunk's intent is satisfied by the correct successor reference. The stale entry is purely metadata noise.

## Fix paths

1. (preferred) Drop the `src/ve.py#remove_external` entry from the chunk's `code_references`. The `src/cli/artifact.py#remove_external` entry already covers the claim.
2. Run `ve chunk update-references` (or equivalent) to let the reference-resolution tooling reconcile both entries automatically.
