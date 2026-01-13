---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/templates/chunk/GOAL.md.jinja2
- src/templates/commands/chunk-create.md.jinja2
- src/templates/commands/chunk-complete.md.jinja2
- tests/test_models.py
code_references:
  - ref: src/models.py#BugType
    implements: "BugType enum with SEMANTIC and IMPLEMENTATION values"
  - ref: src/models.py#ChunkFrontmatter
    implements: "bug_type field added to ChunkFrontmatter model"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "BUG_TYPE documentation section and frontmatter field"
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Step 6: Bug type classification prompting for agents"
  - ref: src/templates/commands/chunk-complete.md.jinja2
    implements: "Bug type-aware backreference and status transition guidance"
  - ref: tests/test_models.py#TestChunkFrontmatterBugType
    implements: "Unit tests for bug_type field validation"
narrative: null
investigation: bug_chunk_semantic_value
subsystems: []
friction_entries: []
created_after:
- background_keyword_semantic
---

# Chunk Goal

## Minor Goal

Add a `bug_type` field to the chunk schema that guides agent behavior at completion time. When a chunk is a bug fix, the agent should classify it as either:

- **`semantic`**: The bug revealed new understanding of intended behavior. This is a discovery—we learned something about how the system should work.
- **`implementation`**: The bug corrected known-wrong code. We knew how it should work; we just built it wrong.

The chunk template should include conditional guidance based on this classification:
- **Semantic bugs** require code backreferences (the fix adds to code understanding) and should search for other chunks that may need updating based on the new understanding. On completion, status → ACTIVE (the chunk asserts ongoing understanding).
- **Implementation bugs** may skip backreferences (they don't add semantic value) and focus purely on the fix. On completion, status → HISTORICAL (point-in-time correction, not an ongoing anchor).

**Context from investigation:** Analysis of existing bug chunks showed that semantic value varies by type. Pure code bugs (typos, null handling) provide low semantic value via backreferences, while bugs that reveal workflow or clarity issues provide high value. This field enables the agent to behave appropriately based on the bug's nature.

## Success Criteria

1. **Schema addition**: `bug_type` field added to chunk frontmatter schema with values `semantic` | `implementation` | `null` (for non-bug chunks)
2. **Template guidance**: Chunk GOAL.md template includes conditional instructions based on bug_type value
3. **Semantic bug guidance**: Template instructs agents to add code backreferences and search for impacted chunks when `bug_type: semantic`
4. **Implementation bug guidance**: Template allows agents to skip backreferences when `bug_type: implementation`, noting they don't add code understanding
5. **Status transition guidance**: Template instructs that on completion, `semantic` bugs → ACTIVE status (ongoing anchor), `implementation` bugs → HISTORICAL status (point-in-time)
6. **Agent prompting**: `/chunk-create` skill prompts agents to classify bug type when creating a bug fix chunk
7. **Validation**: `ve chunk validate` accepts the new field values
8. **Tests**: Unit tests verify schema accepts valid bug_type values

## Relationship to Parent

<!--
DELETE THIS SECTION if parent_chunk is null.

If this chunk modifies work from a previous chunk, explain:
- What deficiency or change prompted this work?
- What from the parent chunk remains valid?
- What is being changed and why?

This context helps agents understand the delta and avoid breaking
invariants established by the parent.
-->