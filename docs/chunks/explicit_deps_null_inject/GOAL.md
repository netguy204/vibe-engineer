---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: explicit_deps_null_semantics
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_unblock_transition
- chunklist_status_filter
---

# Chunk Goal

## Minor Goal

Update the orchestrator's injection logic to distinguish between `depends_on: []` (explicit empty list) and `depends_on: null` or omitted field. Currently, both cases trigger oracle consultation. After this change:

- `depends_on: []` → Set `explicit_deps=True`, bypass oracle (agent explicitly declares no dependencies)
- `depends_on: null` or omitted → Consult oracle as before (agent doesn't know dependencies)

This completes the explicit dependency story from the `explicit_chunk_deps` narrative by allowing agents to declare chunks as truly independent.

## Success Criteria

- When a chunk has `depends_on: []` in its GOAL.md frontmatter, the work unit is created with `explicit_deps=True`
- When a chunk has `depends_on: null` or no `depends_on` field, the work unit has `explicit_deps=False` and oracle is consulted
- Existing behavior for non-empty `depends_on` arrays is preserved
- Tests verify the null vs empty distinction

