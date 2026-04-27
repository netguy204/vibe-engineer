---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models/chunk.py
- src/chunks.py
- src/chunk_validation.py
- src/ve.py
- src/task_utils.py
- src/subsystems.py
- tests/test_models.py
- tests/test_chunks.py
- tests/test_chunk_activate.py
- tests/test_chunk_overlap.py
- tests/test_chunk_validate.py
code_references:
- ref: src/models/chunk.py#ChunkStatus
  implements: Chunk lifecycle status StrEnum with FUTURE, IMPLEMENTING, ACTIVE, SUPERSEDED,
    HISTORICAL values
- ref: src/models/chunk.py#ChunkFrontmatter
  implements: Pydantic model for chunk GOAL.md frontmatter validation with fields for
    status, ticket, parent_chunk, code_paths, code_references, narrative, investigation,
    subsystems, proposed_chunks, dependents, created_after, friction_entries, and bug_type
- ref: src/chunks.py#Chunks::parse_chunk_frontmatter
  implements: Returns typed ChunkFrontmatter | None instead of dict | None
- ref: src/chunks.py#Chunks::get_current_chunk
  implements: Uses ChunkStatus.IMPLEMENTING for status comparison
- ref: src/chunks.py#Chunks::activate_chunk
  implements: Uses ChunkStatus.FUTURE for status comparison
- ref: src/chunks.py#Chunks::find_overlapping_chunks
  implements: Uses ChunkStatus.ACTIVE for status comparison and typed frontmatter
    access
- ref: src/chunk_validation.py#validate_chunk_complete
  implements: Uses typed ChunkStatus and frontmatter.code_references; calls validate_investigation_ref
    and validate_friction_entries_ref
- ref: src/chunks.py#Chunks::validate_investigation_ref
  implements: Validates investigation field reference exists in docs/investigations/ (added by investigation_chunk_refs)
- ref: src/subsystems.py#Subsystems::find_overlapping_subsystems
  implements: Uses typed frontmatter.code_references and frontmatter.code_paths
- ref: tests/test_models.py#TestChunkFrontmatter
  implements: Test suite for ChunkFrontmatter validation
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after:
- external_resolve
---

# Chunk Goal

## Minor Goal

Chunks have a `ChunkStatus` StrEnum and a `ChunkFrontmatter` Pydantic model in the models package, parity with the other workflow artifact types (narratives, investigations, subsystems). This resolves the "Chunk Status Not a StrEnum" deviation documented in the workflow_artifacts subsystem.

`ChunkStatus` defines the chunk lifecycle status values as a StrEnum rather than as comments in a template, providing:
- Compile-time validation of status values
- Type-safe status comparisons (`status == ChunkStatus.IMPLEMENTING`)
- A `ChunkFrontmatter` Pydantic model for consistent frontmatter validation
- Consistency with other workflow types that have StrEnums and models

The result is parity with the other workflow types, enabling:
- Type-safe status handling in code
- Consistent frontmatter validation using Pydantic
- IDE support and autocompletion for chunk statuses
- Foundation for adding `VALID_CHUNK_TRANSITIONS` in a follow-up chunk

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