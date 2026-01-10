---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models.py
  - src/chunks.py
  - src/subsystems.py
  - src/ve.py
  - src/templates/chunk/GOAL.md
  - src/templates/commands/chunk-complete.md
  - tests/test_models.py
  - tests/test_chunks.py
  - tests/test_subsystems.py
  - tests/test_chunk_validate.py
  - tests/test_subsystem_validate.py
  - README.md
  - docs/trunk/SPEC.md
code_references:
  - ref: src/models.py#SubsystemRelationship
    implements: "Pydantic model for chunk-to-subsystem relationship (inverse of ChunkRelationship)"
  - ref: src/chunks.py#Chunks::validate_subsystem_refs
    implements: "Validates subsystem references in chunk frontmatter exist in docs/subsystems/"
  - ref: src/chunks.py#Chunks::validate_chunk_complete
    implements: "Extended to include subsystem reference validation"
  - ref: src/subsystems.py#Subsystems::validate_chunk_refs
    implements: "Validates chunk references in subsystem frontmatter exist in docs/chunks/"
  - ref: src/ve.py#validate
    implements: "Renamed from 'complete' - CLI command for chunk validation"
  - ref: src/ve.py#validate
    implements: "New CLI command 've subsystem validate' for subsystem validation"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "Template updated with subsystems field and documentation"
narrative: 0002-subsystem_documentation
created_after: ["0017-subsystem_template"]
---

# Chunk Goal

## Minor Goal

Enable bidirectional navigation between chunks and subsystems by extending the chunk GOAL.md frontmatter to include a `subsystems` field. This allows agents to see not only what chunks relate to a subsystem (via `SubsystemFrontmatter.chunks`) but also what subsystems a chunk relates to (via chunk frontmatter's `subsystems` field).

This chunk advances the trunk goal's Required Properties ("Following the workflow must maintain the health of documents over time") by making cross-cutting concerns discoverable from both directions—whether you start from a chunk or from a subsystem.

## Success Criteria

1. **Command renamed**: `ve chunk complete` renamed to `ve chunk validate` with all references updated (README.md, SPEC.md, `/chunk-complete` slash command, tests)

2. **Chunk frontmatter schema extended**: Add optional `subsystems` field to chunk GOAL.md frontmatter with entries specifying subsystem ID and relationship type ("implements" or "uses")

3. **SubsystemRelationship model**: Create Pydantic model (inverse of `ChunkRelationship`) with:
   - `subsystem_id`: string matching `{NNNN}-{short_name}` pattern
   - `relationship`: literal "implements" | "uses"

4. **Chunk validation extended**: `ve chunk validate` (formerly `complete`) now also validates:
   - Subsystem IDs referenced in chunk frontmatter exist in `docs/subsystems/`
   - Invalid subsystem_id format produces error

5. **Subsystem validation command**: `ve subsystem validate <subsystem_id>` validates:
   - Chunk IDs referenced in subsystem frontmatter exist in `docs/chunks/`
   - Reports errors for non-existent chunks

6. **Tests**: Unit and CLI tests covering:
   - Valid bidirectional references pass validation
   - Invalid subsystem_id format fails validation
   - Non-existent subsystem reference produces error
   - Non-existent chunk reference produces error