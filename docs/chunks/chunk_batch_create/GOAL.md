---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/templates/claude/CLAUDE.md.jinja2
- tests/test_chunk_start.py
code_references:
- ref: src/ve.py#create
  implements: "CLI command accepting variadic chunk names with batch creation logic"
- ref: src/ve.py#_start_task_chunks
  implements: "Batch chunk creation handler for task directory (cross-repo) mode"
- ref: tests/test_chunk_start.py#TestBatchCreation
  implements: "Test suite for batch chunk creation functionality"
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: "Documentation for batch creation in CLAUDE.md template"
narrative: null
investigation: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: uses
friction_entries: []
bug_type: null
created_after:
- chunklist_external_status
- orch_url_command
---

# Chunk Goal

## Minor Goal

Extend `ve chunk create` to accept multiple chunk names in a single invocation, enabling batch creation of chunks (e.g., when creating all chunks from a narrative's proposed_chunks).

Example:
```bash
ve chunk create auth_login auth_logout auth_refresh --future
```

This reduces the likelihood of agents manually creating GOAL.md files when asked to create multiple chunks at once, since they can accomplish it in one command.

Additionally, update CLAUDE.md template to:
1. Document the batch creation capability
2. Nudge agents to use sub-agents (Task tool) to refine each chunk's goal in parallel after batch creation

## Success Criteria

1. `ve chunk create name1 name2 name3` creates all three chunks with proper templates
2. `--future` flag applies to all chunks in batch
3. `--ticket` flag applies to all chunks in batch (if provided)
4. Command outputs list of created chunk paths
5. CLAUDE.md template documents batch creation usage
6. CLAUDE.md template includes guidance to spawn sub-agents to refine goals in parallel when multiple chunks are created
7. Tests added for batch creation behavior

