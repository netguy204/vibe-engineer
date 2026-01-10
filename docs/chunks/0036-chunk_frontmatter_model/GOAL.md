---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models.py
  - src/chunks.py
  - src/ve.py
  - src/task_utils.py
  - src/subsystems.py
  - tests/test_models.py
  - tests/test_chunks.py
  - tests/test_chunk_activate.py
  - tests/test_chunk_overlap.py
  - tests/test_chunk_validate.py
code_references:
  - ref: src/models.py#ChunkStatus
    implements: "Chunk lifecycle status StrEnum with FUTURE, IMPLEMENTING, ACTIVE, SUPERSEDED, HISTORICAL values"
  - ref: src/models.py#ChunkFrontmatter
    implements: "Pydantic model for chunk GOAL.md frontmatter validation"
  - ref: src/chunks.py#Chunks::parse_chunk_frontmatter
    implements: "Returns typed ChunkFrontmatter | None instead of dict | None"
  - ref: src/chunks.py#Chunks::get_current_chunk
    implements: "Uses ChunkStatus.IMPLEMENTING for status comparison"
  - ref: src/chunks.py#Chunks::activate_chunk
    implements: "Uses ChunkStatus.FUTURE for status comparison"
  - ref: src/chunks.py#Chunks::find_overlapping_chunks
    implements: "Uses ChunkStatus.ACTIVE for status comparison and typed frontmatter access"
  - ref: src/chunks.py#Chunks::validate_chunk_complete
    implements: "Uses typed ChunkStatus and frontmatter.code_references"
  - ref: src/chunks.py#Chunks::validate_subsystem_refs
    implements: "Uses typed frontmatter.subsystems access"
  - ref: src/subsystems.py#Subsystems::find_overlapping_subsystems
    implements: "Uses typed frontmatter.code_references and frontmatter.code_paths"
  - ref: tests/test_models.py#TestChunkFrontmatter
    implements: "Test suite for ChunkFrontmatter validation"
narrative: null
subsystems:
  - subsystem_id: "0002-workflow_artifacts"
    relationship: implements
created_after: ["0035-external_resolve"]
---

# Chunk Goal

## Minor Goal

Add `ChunkStatus` StrEnum and `ChunkFrontmatter` Pydantic model to `models.py` to bring chunks in line with the other workflow artifact types (narratives, investigations, subsystems). This resolves the "Chunk Status Not a StrEnum" deviation documented in the workflow_artifacts subsystem.

Currently, chunk status values (FUTURE, IMPLEMENTING, ACTIVE, SUPERSEDED, HISTORICAL) are only defined in template comments. This means:
- No compile-time validation of status values
- Status checked via string comparison (`status == "IMPLEMENTING"`)
- No `ChunkFrontmatter` Pydantic model for consistent frontmatter validation
- Inconsistent with other workflow types that have proper StrEnums and models

This chunk establishes parity with the other workflow types, enabling:
- Type-safe status handling in code
- Consistent frontmatter validation using Pydantic
- IDE support and autocompletion for chunk statuses
- Foundation for adding `VALID_CHUNK_TRANSITIONS` in a future chunk

## Success Criteria

1. **ChunkStatus StrEnum defined in models.py**
   - Contains all five status values: FUTURE, IMPLEMENTING, ACTIVE, SUPERSEDED, HISTORICAL
   - Follows the pattern established by `SubsystemStatus`, `InvestigationStatus`, `NarrativeStatus`
   - Has docstring explaining each status value

2. **ChunkFrontmatter Pydantic model defined in models.py**
   - Fields: status (ChunkStatus), ticket (optional str), parent_chunk (optional str), code_paths (list[str]), code_references (list[SymbolicReference]), narrative (optional str), subsystems (list[SubsystemRelationship]), proposed_chunks (list[ProposedChunk])
   - Follows the pattern of `SubsystemFrontmatter`, `InvestigationFrontmatter`, `NarrativeFrontmatter`

3. **chunks.py updated to use ChunkFrontmatter**
   - `parse_chunk_frontmatter()` returns `ChunkFrontmatter | None` instead of `dict | None`
   - All call sites updated to use typed model access (e.g., `frontmatter.status` instead of `frontmatter.get("status")`)

4. **All existing tests pass**
   - No behavioral changes, only type safety improvements

5. **Chunk backreference added to models.py**
   - Comment referencing this chunk for the new code