---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- tests/test_chunk_list.py
code_references:
  - ref: src/cli/chunk.py#_parse_status_filters
    implements: "Parse and validate status filters from CLI options (--status, --future, --active, --implementing)"
  - ref: src/cli/chunk.py#list_chunks
    implements: "CLI command with status filtering options and mutual exclusivity validation"
  - ref: src/cli/chunk.py#_format_grouped_artifact_list
    implements: "Status filtering for task context (cross-repo) chunk listing"
  - ref: src/cli/chunk.py#_list_task_chunks
    implements: "Task context chunk listing with status filter parameter"
  - ref: tests/test_chunk_list.py#TestStatusFiltering
    implements: "Tests for status filtering in 've chunk list' command"
  - ref: tests/test_chunk_list.py#TestStatusConvenienceFlags
    implements: "Tests for convenience flags --future, --active, --implementing"
  - ref: tests/test_chunk_list.py#TestStatusFilterMutualExclusivity
    implements: "Tests for mutual exclusivity between status filters and output mode flags"
  - ref: tests/test_chunk_list.py#TestStatusFilterWithExternalChunks
    implements: "Tests for status filtering with external chunk references"
narrative: null
investigation: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: uses
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_task_agent_env
- orch_task_detection
- explicit_deps_batch_inject
- explicit_deps_chunk_propagate
- explicit_deps_goal_template
- explicit_deps_proposed_schema
- explicit_deps_skip_oracle
- explicit_deps_workunit_flag
---

# Chunk Goal

## Minor Goal

Add status filtering to `ve chunk list` so operators can quickly find chunks by lifecycle state. Currently, listing chunks requires manually scanning output or piping through grep. Native filtering reduces friction when managing large chunk sets.

## Success Criteria

- `ve chunk list --status FUTURE` shows only FUTURE chunks
- `ve chunk list --status ACTIVE` shows only ACTIVE chunks
- `ve chunk list --status IMPLEMENTING` shows only IMPLEMENTING chunks
- Status values are case-insensitive (`--status future` works)
- Convenience aliases exist for common filters:
  - `--future` equivalent to `--status FUTURE`
  - `--active` equivalent to `--status ACTIVE`
  - `--implementing` equivalent to `--status IMPLEMENTING`
- Multiple statuses can be specified: `--status FUTURE --status ACTIVE` or `--status FUTURE,ACTIVE`
- Invalid status values produce a helpful error listing valid options
- Existing flags (`--latest`, repo source flags) compose correctly with status filter
- Help text documents the new options