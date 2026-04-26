---
discovered_by: audit batch 10h
discovered_at: 2026-04-26T02:29:26Z
severity: medium
status: open
artifacts:
  - docs/chunks/subsystem_schemas_and_model/GOAL.md
---

# Claim

`docs/chunks/subsystem_schemas_and_model/GOAL.md` declares the following in
its frontmatter:

```
code_paths:
- src/models.py
- src/subsystems.py
- tests/test_subsystems.py
code_references:
- ref: src/models.py#SubsystemStatus
  implements: Status enum for subsystem documentation lifecycle ...
- ref: src/models.py#ChunkRelationship
  ...
- ref: src/models.py#ChunkRelationship::validate_chunk_id
  ...
- ref: src/models.py#SubsystemFrontmatter
  ...
```

Success criterion #5 also states: "All models are added to `src/models.py`
following existing Pydantic patterns."

# Reality

`src/models.py` does not exist. `src/models/` is a package directory:

```
ls src/models/
__init__.py  __pycache__  chunk.py  entity.py  friction.py
investigation.py  narrative.py  references.py  reviewer.py
shared.py  subsystem.py
```

The actual symbols live across two files:

- `SubsystemStatus`, `SubsystemFrontmatter` → `src/models/subsystem.py`
- `ChunkRelationship`, `ChunkRelationship.validate_chunk_id` →
  `src/models/references.py` (line 154)

The chunk's last three `code_references` already point to the correct
post-split locations (`src/models/references.py#ChunkRelationship`,
`src/models/subsystem.py#SubsystemStatus`,
`src/models/subsystem.py#SubsystemFrontmatter`), so the broken first four
references are duplicates that were never cleaned up after the
`src/models.py → src/models/` package split. `src/subsystems.py` and
`tests/test_subsystems.py` exist and are correct.

The post-state described by the chunk (the schemas, model, validation,
utility class, tests) actually exists; only the file paths are stale.

# Workaround

Prose was not rewritten this session — the broken `code_paths`/
`code_references` constitute undeclared over-claim about the system's
shape, which fires the audit's veto rule. The split into `src/models.py`
versus `src/models/<name>.py` is also not a single-file fix-in-place
candidate (one file became multiple files), so it can't be auto-corrected.

# Fix paths

1. **Preferred:** A follow-up metadata-cleanup chunk should remove the
   four stale `src/models.py#X` entries from `code_references`, drop
   `src/models.py` from `code_paths` (replacing it with
   `src/models/subsystem.py` and `src/models/references.py`), and update
   success criterion #5 to reflect the package layout. The duplicate
   references at the bottom of the list confirm the migration was
   recognized but not finished.
2. **Alternative:** Re-introduce a `src/models.py` shim that re-exports
   from the package, but this only papers over the staleness without
   correcting the chunk's record of where its symbols live.
