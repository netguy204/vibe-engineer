---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/chunk/GOAL.md.jinja2
code_references:
- ref: src/templates/chunk/GOAL.md.jinja2
  implements: "depends_on field in frontmatter and schema documentation for explicit chunk dependencies"
narrative: explicit_chunk_deps
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_task_worktrees
---

# Chunk Goal

## Minor Goal

The chunk GOAL.md Jinja2 template carries a `depends_on` field, so agents can explicitly declare dependencies on other chunks. This field provides an escape hatch from the orchestrator's conflict oracle - when a chunk has explicit dependencies, those dependencies become authoritative and bypass heuristic auto-detection entirely.

This is the foundational schema change for the explicit_chunk_deps narrative. The field must exist in the template before other narrative chunks can implement propagation logic (chunk-create translation) or orchestrator integration (batch injection, oracle bypass).

## Success Criteria

- The `depends_on` field is added to `src/templates/chunk/GOAL.md.jinja2` frontmatter with default value `[]`
- The field accepts a list of chunk directory name strings (e.g., `["auth_api", "auth_client"]`)
- Schema documentation is added to the template's comment block explaining:
  - Purpose: declares explicit dependencies that bypass the oracle's auto-detection
  - Scope: intra-batch scheduling (dependencies express order within a single injection batch)
  - Format: list of chunk directory names (strings, not indices)
  - Behavior: when non-empty, the orchestrator uses these dependencies instead of running conflict detection
- The `ve init` command successfully renders projects using the updated template
- Existing chunks without `depends_on` continue to work (field defaults to empty list)