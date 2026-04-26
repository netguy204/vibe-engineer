---
discovered_by: audit batch 10j (intent_active_audit)
discovered_at: 2026-04-26T02:30:03Z
severity: low
status: open
artifacts:
  - docs/chunks/chunk_frontmatter_model/GOAL.md
---

## Claim

`docs/chunks/chunk_frontmatter_model/GOAL.md` Success Criteria reference `models.py` as the home of the new symbols:

- "ChunkStatus StrEnum defined in models.py"
- "ChunkFrontmatter Pydantic model defined in models.py"
- "Chunk backreference added to models.py"

## Reality

`src/models.py` no longer exists. The `models` module was split into a package at `src/models/` by the `models_subpackage` chunk. The actual symbols now live at:

- `ChunkStatus` → `src/models/chunk.py` (line 20)
- `ChunkFrontmatter` → `src/models/chunk.py` (line 58)
- Chunk backreference comment → `src/models/chunk.py` (line 18)

The chunk's `code_paths` and `code_references` already point to `src/models/chunk.py`, so the staleness is confined to the prose of the Success Criteria block, not the structured frontmatter.

## Workaround

None needed at runtime — the chunk's structured fields point to the correct files. The audit batch did not edit the success criteria (they are off-limits per the audit's action rules).

## Fix paths

1. **Update Success Criteria prose** to reference `src/models/chunk.py` instead of `models.py`. This is a doc-only fix; the underlying claims (the enum and model exist) are still true.
2. Leave as-is — `code_paths` and `code_references` carry the canonical pointers, and the prose staleness is harmless for current callers. Revisit if a future readers' confusion arises.
