---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/chunk/GOAL.md.jinja2
code_references:
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "DEPENDS_ON section documenting null vs empty semantics for orchestrator scheduling"
narrative: explicit_deps_null_semantics
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- explicit_deps_null_inject
created_after:
- orch_unblock_transition
- chunklist_status_filter
---

# Chunk Goal

## Minor Goal

Update the chunk GOAL.md template (`src/templates/chunks/GOAL.md.jinja2`) to document the null vs empty semantics for the `depends_on` field:

| Value | Meaning | Oracle behavior |
|-------|---------|-----------------|
| `null` or omitted | "I don't know my dependencies" | Consult oracle |
| `[]` (empty list) | "I explicitly have no dependencies" | Bypass oracle |
| `["chunk_a"]` | "I depend on these chunks" | Bypass oracle |

This ensures agents understand how to declare chunks as independent without triggering oracle consultation.

## Success Criteria

- The `DEPENDS_ON` section in the GOAL.md template explains the null vs empty distinction
- Template includes a clear table or examples showing when to use each form
- Running `ve init` regenerates rendered files with the updated documentation

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