---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/narrative/OVERVIEW.md.jinja2
- src/templates/investigation/OVERVIEW.md.jinja2
code_references:
- ref: src/templates/narrative/OVERVIEW.md.jinja2
  implements: "Documents null vs empty semantics for depends_on in proposed_chunks"
- ref: src/templates/investigation/OVERVIEW.md.jinja2
  implements: "Documents null vs empty semantics for depends_on in proposed_chunks"
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

Update the narrative and investigation OVERVIEW.md templates to document the null vs empty semantics for the `depends_on` field in `proposed_chunks` entries:

| Value | Meaning | Oracle behavior |
|-------|---------|-----------------|
| omitted | "I don't know dependencies for this chunk" | Consult oracle |
| `[]` (empty list) | "This chunk explicitly has no dependencies" | Bypass oracle |
| `[0, 2]` | "This chunk depends on prompts at indices 0 and 2" | Bypass oracle |

This ensures agents creating narratives and investigations understand how to declare chunks as independent.

## Success Criteria

- Narrative template (`src/templates/narratives/OVERVIEW.md.jinja2`) explains null vs empty semantics
- Investigation template (`src/templates/investigations/OVERVIEW.md.jinja2`) has the same clarification
- The `proposed_chunks` schema documentation is updated in both templates

