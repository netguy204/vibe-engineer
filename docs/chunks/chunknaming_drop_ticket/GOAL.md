---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/chunks.py
- src/ve.py
- src/task_utils.py
- src/templates/commands/chunk-create.md.jinja2
- tests/test_chunks.py
code_references:
- ref: src/chunks.py#Chunks::find_duplicates
  implements: "Collision detection ignoring ticket_id (matches on short_name only)"
- ref: src/chunks.py#Chunks::create_chunk
  implements: "Directory naming without ticket suffix (ticket in frontmatter only)"
- ref: src/ve.py#validate_combined_chunk_name
  implements: "Validation simplified to check only short_name length"
- ref: src/task_utils.py#create_task_chunk
  implements: "Task context chunk creation without ticket in directory name"
narrative: null
investigation: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
- subsystem_id: cluster_analysis
  relationship: uses
friction_entries: []
bug_type: null
created_after:
- validation_chunk_name
---

# Chunk Goal

## Minor Goal

Stop including ticket IDs in chunk directory names while preserving ticket association in frontmatter.

Currently, when a ticket is provided during chunk creation, the chunk directory is named `{short_name}-{ticket_id}` (e.g., `auth_refactor-PROJ-123`). This embeds external tracking system identifiers into the filesystem structure, which:

1. Creates visual noise in `docs/chunks/` listings
2. Couples internal naming to external systems
3. Makes chunk names less memorable and harder to type

The ticket association should remain in the `ticket` frontmatter field where it belongs, allowing tooling to query "which chunk addresses ticket X?" without polluting directory names.

## Success Criteria

- `ve chunk create my_chunk PROJ-123` creates directory `docs/chunks/my_chunk/` (not `docs/chunks/my_chunk-PROJ-123/`)
- The `ticket` field in GOAL.md frontmatter is still populated with the ticket ID
- The `/chunk-create` skill still prompts the agent to identify any associated ticket
- `find_duplicates()` no longer considers ticket IDs when checking for collisions
- Existing chunks with ticket suffixes continue to work (backward compatibility)
- Tests updated to reflect new naming behavior