---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models.py
  - src/chunks.py
  - src/templates/chunk/GOAL.md.jinja2
  - tests/test_chunk_validate.py
code_references:
  - ref: src/models.py#FrictionEntryReference
    implements: "Pydantic model for friction entry reference with entry_id and scope fields"
  - ref: src/models.py#FRICTION_ENTRY_ID_PATTERN
    implements: "Regex pattern for validating friction entry ID format (F followed by digits)"
  - ref: src/models.py#ChunkFrontmatter
    implements: "Added friction_entries field to chunk frontmatter schema"
  - ref: src/chunks.py#Chunks::validate_friction_entries_ref
    implements: "Validation method checking friction entry references exist in FRICTION.md"
  - ref: src/chunks.py#Chunks::validate_chunk_complete
    implements: "Integration of friction entry validation into chunk completion validation"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "Template with friction_entries field and documentation comment explaining format"
  - ref: tests/test_chunk_validate.py#TestFrictionEntryRefValidation
    implements: "Test class validating friction entry reference validation behavior"
narrative: null
investigation: friction_log_artifact
subsystems: []
created_after:
- orch_attention_queue
- orch_conflict_oracle
- orch_agent_skills
- orch_question_forward
---

# Chunk Goal

## Minor Goal

Add `friction_entries` to the chunk GOAL.md template, enabling bidirectional linking between chunks and the friction entries they address.

This provides traceability from "why did we do this work?" back to accumulated pain points. When reviewing a chunk, you can see which friction it resolved; when reviewing friction, you can see which chunks addressed it.

## Success Criteria

- Chunk GOAL.md template includes `friction_entries` in frontmatter schema
- Format: `friction_entries: [{entry_id: "F001", scope: "full"}, ...]`
  - `entry_id`: References a friction entry ID (e.g., "F001")
  - `scope`: "full" (chunk fully addresses) or "partial" (chunk partially addresses)
- `ve chunk validate` validates that referenced friction entries exist in FRICTION.md
- Documentation comment in template explains the field's purpose and format
- Template guidance explains when to populate this field (during /chunk-create if addressing known friction)

## Dependencies

Requires `friction_template_and_cli` chunk to be implemented first (FRICTION.md must exist for validation).