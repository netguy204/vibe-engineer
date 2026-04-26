---
discovered_by: audit batch 9c
discovered_at: 2026-04-26T02:21:37Z
severity: low
status: open
artifacts:
  - docs/chunks/narrative_consolidation/GOAL.md
---

# Stale code_references in narrative_consolidation

## Claim

`docs/chunks/narrative_consolidation/GOAL.md` `code_references` (lines 6-32) names symbols at these paths:

- `src/chunks.py#BackreferenceInfo`
- `src/chunks.py#count_backreferences`
- `src/chunks.py#ConsolidationResult`
- `src/chunks.py#ClusterResult`
- `src/chunks.py#cluster_chunks`
- `src/chunks.py#consolidate_chunks`
- `src/chunks.py#update_backreferences`
- `src/ve.py#backrefs`
- `src/ve.py#cluster`
- `src/ve.py#compact`
- `src/ve.py#update_refs`

## Reality

The CLI was modularized (chunk `cli_modularize`) and `src/ve.py` is now a thin shim — it does not define `backrefs`, `cluster`, `compact`, or `update_refs`. The symbols live at:

- `src/cli/chunk.py#backrefs` (line 1057)
- `src/cli/chunk.py#cluster` (line 1110)
- `src/cli/narrative.py#compact` (line 239)
- `src/cli/narrative.py#update_refs` (line 289)

The consolidation symbols claimed at `src/chunks.py` are imported there but defined elsewhere:

- `BackreferenceInfo`, `count_backreferences`, `update_backreferences` → `src/backreferences.py`
- `ConsolidationResult`, `consolidate_chunks` → `src/consolidation.py`
- `ClusterResult`, `cluster_chunks` → `src/cluster_analysis.py`

Verification:

```
grep -n "class BackreferenceInfo\|def count_backreferences\|class ConsolidationResult\|class ClusterResult\|def cluster_chunks\|def consolidate_chunks\|def update_backreferences" src/chunks.py src/backreferences.py src/consolidation.py src/cluster_analysis.py
```

returns hits only in the dedicated modules; `src/chunks.py` only re-imports them.

## Workaround

None needed for this audit pass — the symbols exist and behave as described, only their location moved. No prose rewrite was attempted (no retrospective framing tells in the narrative_consolidation prose itself).

## Fix paths

1. **(preferred)** Update `code_references` in `docs/chunks/narrative_consolidation/GOAL.md` to point at the new module paths (`src/backreferences.py`, `src/consolidation.py`, `src/cluster_analysis.py`, `src/cli/chunk.py`, `src/cli/narrative.py`). Mechanical fix; no intent change.
2. Re-export the symbols from `src/chunks.py` and `src/ve.py` so the references resolve. Worse — re-introduces the monolith pattern that `cli_modularize` and chunks decomposition explicitly removed.
