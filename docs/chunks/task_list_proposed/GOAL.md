---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/task_utils.py
- src/ve.py
- tests/test_chunk_list_proposed.py
code_references:
  - ref: src/task_utils.py#list_task_proposed_chunks
    implements: "Aggregates proposed chunks from external repo + all project repos in task context"
  - ref: src/ve.py#_format_proposed_chunks_by_source
    implements: "Formats proposed chunks grouped by source artifact"
  - ref: src/ve.py#_format_grouped_proposed_chunks
    implements: "Formats and displays grouped proposed chunk listing output for task mode"
  - ref: src/ve.py#_list_task_proposed_chunks
    implements: "Handler for proposed chunk listing in task directory context"
  - ref: src/ve.py#list_proposed_chunks_cmd
    implements: "Task-aware CLI command that detects task context and delegates appropriately"
  - ref: tests/test_chunk_list_proposed.py#TestListProposedChunksTaskContext
    implements: "Tests for task context detection, collection, and output format"
  - ref: tests/test_chunk_list_proposed.py#TestListTaskProposedChunksLogic
    implements: "Tests for list_task_proposed_chunks business logic"
narrative: null
subsystems: []
created_after:
- artifact_promote
- task_qualified_refs
- task_init_scaffolding
- task_status_command
- task_config_local_paths
---

# Chunk Goal

## Minor Goal

Make `ve chunk list-proposed` work in a task context by aggregating proposed chunks from all repositories in the task (external artifact repo + all project repos). When run from a task directory (containing `.ve-task.yaml`), the command should:

1. Detect that it's in a task context
2. Collect proposed chunks from the external artifact repository
3. Collect proposed chunks from each project repository
4. Display results grouped by source repository (similar to how `ve task status` groups artifacts)

This enables multi-repo workflows to have visibility into all pending work across the task, not just within a single project.

## Success Criteria

1. **Task context detection**: Running `ve chunk list-proposed` from a task directory detects the task context and aggregates from all repos
2. **External repo collection**: Proposed chunks from investigations, narratives, and subsystems in the external artifact repo are collected
3. **Project repo collection**: Proposed chunks from each project in `config.projects` are collected
4. **Grouped output**: Results are displayed grouped by repository using the same header format as `ve chunk list`:
   - `# External Artifacts ({repo})` for the external artifact repo
   - `# {repo} (local)` for each project repo
   - Empty sections display "No proposed chunks" (not omitted)
   - Within each repo section, proposed chunks are grouped by source artifact (e.g., `From docs/investigations/foo:`)
5. **Backwards compatible**: Running from a regular project directory (no `.ve-task.yaml`) continues to work as before (single project)
6. **All tests pass**: New tests for task-context behavior, existing tests continue to pass

