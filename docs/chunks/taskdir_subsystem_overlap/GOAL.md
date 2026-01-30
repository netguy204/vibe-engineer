---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- tests/test_subsystem_overlap_cli.py
code_references:
  - ref: src/ve.py#overlap
    implements: "Task-aware subsystem overlap command that resolves chunks across external and project repos"
  - ref: tests/test_subsystem_overlap_cli.py#TestSubsystemOverlapInTaskContext
    implements: "Tests for task context chunk resolution and subsystem overlap detection"
  - ref: tests/test_subsystem_overlap_cli.py#TestSubsystemOverlapOutsideTaskContext
    implements: "Regression tests ensuring single-repo behavior is unchanged"
narrative: null
investigation: null
subsystems:
- subsystem_id: cross_repo_operations
  relationship: uses
friction_entries: []
bug_type: null
created_after:
- taskdir_cli_guidance
- chunk_batch_create
---

# Chunk Goal

## Minor Goal

Make `ve subsystem overlap` work correctly in task contexts by resolving chunks through the task's external artifacts system instead of only looking locally.

Currently, when running `ve subsystem overlap <chunk_name>` from within a task directory, the command fails with "Chunk not found" even when the chunk exists in the external artifacts repo. The command should resolve external chunks the same way other task-aware commands do.

## Success Criteria

- `ve subsystem overlap <chunk>` works when run from a task directory where the chunk exists in the external artifacts repo
- External chunks are resolved using the same mechanism as other task-aware commands
- Local chunks continue to work as before (no regression)
- Error messages are helpful when a chunk genuinely doesn't exist (vs. resolution failure)

