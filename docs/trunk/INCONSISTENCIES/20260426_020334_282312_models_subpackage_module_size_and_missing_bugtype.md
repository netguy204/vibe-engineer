---
discovered_by: audit batch 7d (intent_active_audit)
discovered_at: 2026-04-26T02:03:34Z
severity: low
status: open
artifacts:
  - docs/chunks/models_subpackage/GOAL.md
  - src/models/references.py
  - src/models/chunk.py
---

## Claim

`docs/chunks/models_subpackage/GOAL.md` (Success Criteria):

> Single-responsibility modules: Each new module under `models/` contains only the types, enums, constants, and validators for one artifact domain. **No module exceeds ~200 lines.**

Minor Goal also enumerates the contents of `models/chunk.py` as:

> `ChunkStatus`, **BugType**, `VALID_CHUNK_TRANSITIONS`, `ChunkFrontmatter`, `ChunkDependent`.

## Reality

Two mismatches:

1. `wc -l src/models/references.py` reports **390 lines** — nearly double the per-module size criterion. Other modules conform: chunk.py (133), entity.py (175), friction.py (138), reviewer.py (151), shared.py (82), and the smaller ones are well under.
2. `BugType` is not defined anywhere under `src/models/` (`grep -rn "BugType" src/models/` returns no matches). The chunk lists it as part of `models/chunk.py`, but the symbol does not exist post-split. (This may be a stale enumeration carried over from the pre-split `src/models.py` or a planned addition that never landed.)

Reproduction:

```
$ wc -l src/models/references.py
390 src/models/references.py
$ grep -rn "BugType" src/models/
(no output)
```

## Workaround

None applied. The package re-exports work and the rest of the documented symbols exist where claimed.

## Fix paths

1. Split `models/references.py` into smaller cohesive submodules (e.g., separate symbolic/code refs from cross-artifact relationship models) to satisfy the ≤200-line criterion, and remove `BugType` from the chunk's enumeration if the symbol is not coming back.
2. Relax the per-module line ceiling in this chunk's Success Criteria to match the achieved decomposition, and either reintroduce `BugType` or strike it from the chunk text.
