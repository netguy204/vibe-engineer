---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references:
  - ref: src/models.py#ChunkFrontmatter
    implements: "depends_on field type changed to list[str] | None = None to preserve null vs empty distinction"
  - ref: src/ve.py#read_chunk_dependencies
    implements: "Returns None vs [] to signal unknown vs explicit-no-deps"
  - ref: src/ve.py#orch_inject
    implements: "Sets explicit_deps=True when depends_on is a list (even empty), omits for None"
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

The orchestrator's injection logic distinguishes between `depends_on: []` (explicit empty list) and `depends_on: null` or omitted field:

- `depends_on: []` → Sets `explicit_deps=True`, bypasses oracle (agent explicitly declares no dependencies)
- `depends_on: null` or omitted → Consults oracle (agent doesn't know dependencies)

This completes the explicit dependency story from the `explicit_chunk_deps` narrative by allowing agents to declare chunks as truly independent.

## Success Criteria

- When a chunk has `depends_on: []` in its GOAL.md frontmatter, the work unit is created with `explicit_deps=True`
- When a chunk has `depends_on: null` or no `depends_on` field, the work unit has `explicit_deps=False` and oracle is consulted
- Existing behavior for non-empty `depends_on` arrays is preserved
- Tests verify the null vs empty distinction

