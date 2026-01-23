---
status: SUPERSEDED
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/scratchpad.py
- tests/test_scratchpad.py
- tests/test_ve_scratchpad.py
code_references:
  - ref: src/scratchpad.py#ScratchpadEntry
    implements: "Data class for individual scratchpad entries with context, type, name, status, created_at"
  - ref: src/scratchpad.py#ScratchpadListResult
    implements: "Result container grouping entries by context with total count"
  - ref: src/scratchpad.py#Scratchpad::_collect_entries_for_context
    implements: "Internal method to collect chunk and narrative entries from a single context"
  - ref: src/scratchpad.py#Scratchpad::list_all
    implements: "Cross-project listing with artifact_type, context_type, and status filtering"
  - ref: src/scratchpad.py#Scratchpad::list_context
    implements: "Single-context listing for current project mode"
  - ref: src/ve.py#scratchpad
    implements: "CLI command group for scratchpad operations"
  - ref: src/ve.py#scratchpad_list
    implements: "CLI command: ve scratchpad list with --all, --tasks, --projects, --status filters"
narrative: global_scratchpad
investigation: bidirectional_doc_code_sync
subsystems:
  - subsystem_id: workflow_artifacts
    relationship: implements
friction_entries: []
bug_type: null
created_after: []
---

# Chunk Goal

## Minor Goal

Implement cross-project scratchpad queries via `ve scratchpad list`. This enables the "What am I working on?" use case - seeing all work-in-progress across all projects and tasks from a single command.

**Depends on**: `scratchpad_storage` (needs storage infrastructure)

**Can run in parallel with**: `scratchpad_chunk_commands`, `scratchpad_narrative_commands`

## Success Criteria

1. **`ve scratchpad list`**: Lists all entries (chunks + narratives) in current project's scratchpad
2. **`ve scratchpad list --all`**: Lists entries across ALL projects and tasks
3. **`ve scratchpad list --tasks`**: Lists only task entries (`task:*`)
4. **`ve scratchpad list --projects`**: Lists only project entries (non-task)
5. **Grouping**: Output grouped by project/task for readability
6. **Status filtering**: Option to filter by chunk/narrative status
7. **Tests pass**: Unit tests for cross-project queries

### Example Output

```bash
$ ve scratchpad list --all

vibe-engineer/
  chunks:
    - scratchpad_storage (FUTURE)
    - scratchpad_chunk_commands (FUTURE)
  narratives:
    - global_scratchpad (DRAFTING)

pybusiness/
  chunks:
    - fix_commitment_calc (IMPLEMENTING)

task:cloud-migration/
  chunks:
    - migrate_auth_service (IMPLEMENTING)
  narratives:
    - cloud_migration (ACTIVE)
```