---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/chunks.py
- src/templates/chunk/GOAL.md.jinja2
- CLAUDE.md
- .claude/commands/chunk-create.md
- tests/test_chunk_validate.py
code_references:
  - ref: src/models.py#ChunkFrontmatter
    implements: "Optional investigation field in chunk frontmatter schema"
  - ref: src/chunks.py#Chunks::validate_investigation_ref
    implements: "Validation that referenced investigations exist"
  - ref: src/chunks.py#Chunks::validate_chunk_complete
    implements: "Integration of investigation validation into chunk completion"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "Template with investigation field and documentation in comment block"
  - ref: CLAUDE.md
    implements: "Documentation of investigation field in Chunk Frontmatter References section"
  - ref: .claude/commands/chunk-create.md
    implements: "Workflow guidance for populating investigation field from proposed_chunks"
  - ref: tests/test_chunk_validate.py#TestInvestigationRefValidation
    implements: "Tests for investigation reference validation"
narrative: null
subsystems: []
created_after:
- audit_seqnum_refs
---

# Chunk Goal

## Minor Goal

When chunks are created from investigations (via `/investigation-create` → proposed chunks → `/chunk-create`), the chunk's frontmatter should include an `investigation` field that references the originating investigation. This enables implementing agents to discover the exploratory context, findings, and reasoning that led to the chunk's creation, improving implementation quality and decision-making.

This advances the project's goal of documentation-driven development by strengthening the traceability between exploratory work and implementation work.

## Success Criteria

1. **Schema updated**: Chunk GOAL.md frontmatter schema includes an optional `investigation` field (string, nullable) that holds the investigation directory name
2. **CLAUDE.md documented**: The Chunk Frontmatter References section in CLAUDE.md documents the `investigation` field alongside the existing `narrative` and `subsystems` fields
3. **Template updated**: The chunk GOAL.md template comment block includes documentation for the `investigation` field explaining its purpose and usage
4. **Validation support**: `ve chunk validate` checks that referenced investigations exist in `docs/investigations/`
5. **Workflow integration**: When a chunk is created from an investigation's `proposed_chunks`, the `/chunk-create` skill prompts the agent to populate the `investigation` field

