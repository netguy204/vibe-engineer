---
discovered_by: audit batch 7h (intent_active_audit)
discovered_at: 2026-04-26T02:04:13
severity: medium
status: open
artifacts:
  - docs/chunks/chunks_decompose/GOAL.md
---

## Claim

`docs/chunks/chunks_decompose/GOAL.md` makes two load-bearing claims that current code contradicts:

1. **Success Criterion #5** (line 76): "**Core Chunks size reduction**: The Chunks class in `src/chunks.py` shrinks to approximately 800 lines or fewer, focused on CRUD operations..."

2. **Success Criterion #4** (lines 73-74): "**Cross-artifact validation migration**: The four validation methods (validate_subsystem_refs, validate_investigation_ref, validate_narrative_ref, validate_friction_entries_ref) are **moved from the Chunks class to `src/integrity.py`** where they belong conceptually."

The body prose at line 57 also asserts: "After this decomposition, the core Chunks class will shrink to approximately 800 lines focused purely on CRUD and lifecycle management..."

## Reality

1. **Size target missed by 35%.** `wc -l src/chunks.py` reports 1079 lines, not "approximately 800 or fewer". This exceeds the explicit success-criterion target by ~280 lines (35% over).

2. **Validation methods were not moved, only delegated.** `validate_subsystem_refs`, `validate_investigation_ref`, and `validate_narrative_ref` still live in the `Chunks` class (`src/chunks.py:918`, `:940`, `:962`). They are wrapper methods that route through `IntegrityValidator.validate_chunk()` (this is what `code_references` actually documents — "Wrapper method routing through IntegrityValidator.validate_chunk() with filtering"). The chunk's own `code_references` honestly describe the wrapper pattern, but the goal prose and success criterion #4 claim the methods were "moved", not "delegated via wrappers". `validate_friction_entries_ref` does not appear in `chunks.py` at all — search returned no matches for that exact name; either it was renamed or removed without updating the goal.

Reproduction:

```
$ wc -l src/chunks.py
1079 src/chunks.py

$ grep -n "def validate_subsystem_refs\|def validate_investigation_ref\|def validate_narrative_ref\|def validate_friction_entries_ref" src/chunks.py
918:    def validate_subsystem_refs(self, chunk_id: str) -> list[str]:
940:    def validate_investigation_ref(self, chunk_id: str) -> list[str]:
962:    def validate_narrative_ref(self, chunk_id: str) -> list[str]:
```

The other extraction claims (backreferences.py, consolidation.py, cluster_analysis.py, integrity.py.validate_chunk) all verify correctly — those files exist with the named symbols. Only the size target and the "moved vs wrapped" framing are off.

## Workaround

None taken in this audit pass. Veto fired (undeclared over-claim against named success criteria), so no tense rewrite applied to the prose. Goal text left intact.

## Fix paths

1. **Update success criteria to match what shipped.** Reframe #4 as "delegated through wrappers" or "the active logic lives in `IntegrityValidator.validate_chunk()`; `Chunks` retains thin wrappers for back-compat". Reframe #5 with the actual line count or drop the numeric target. Drop `validate_friction_entries_ref` from the criterion if it was intentionally removed.

2. **Finish the work.** Delete the four wrapper methods from `Chunks` (migrating callers to `IntegrityValidator` directly), and continue extracting non-CRUD code from `chunks.py` until the line count approaches the original 800-line target.

Path 1 is preferred unless a follow-up chunk is already scoped to do the remaining decomposition.
