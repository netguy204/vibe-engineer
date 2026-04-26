---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/subsystem.py
- tests/test_subsystem_overlap_cli.py
code_references:
  - ref: src/cli/subsystem.py#overlap
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

`ve subsystem overlap` resolves chunks through the task's external artifacts system when run from a task directory, not just from the local repo.

When invoked from a task directory, the command first looks up the chunk in the external artifacts repo (per `.ve-task.yaml`) and falls back to local resolution otherwise. Outside a task context, it behaves the same as before — searching only the local repo.

## Success Criteria

- `ve subsystem overlap <chunk>` works when run from a task directory where the chunk exists in the external artifacts repo
- External chunks are resolved using the same mechanism as other task-aware commands
- Local chunks continue to work as before (no regression)
- Error messages are helpful when a chunk genuinely doesn't exist (vs. resolution failure)

