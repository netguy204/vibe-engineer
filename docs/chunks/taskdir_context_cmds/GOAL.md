---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/chunks.py
- src/task_utils.py
- src/ve.py
- tests/test_task_context_cmds.py
- docs/subsystems/workflow_artifacts/OVERVIEW.md
code_references:
- ref: src/task_utils.py#resolve_project_qualified_ref
  implements: Parse and resolve project-qualified code references (e.g., "project::src/foo.py#Bar")
- ref: src/task_utils.py#TaskOverlapError
  implements: Error class for task-aware overlap detection
- ref: src/task_utils.py#TaskOverlapResult
  implements: Result dataclass for task overlap detection with repo-prefixed chunk names
- ref: src/task_utils.py#find_task_overlapping_chunks
  implements: Task-aware chunk overlap detection across external and project repos
- ref: src/task_utils.py#_compute_cross_project_overlap
  implements: Cross-project reference overlap computation with symbol hierarchy
- ref: src/task_utils.py#TaskActivateError
  implements: Error class for task-aware chunk activation
- ref: src/task_utils.py#activate_task_chunk
  implements: Task-aware chunk activation across external and project repos
- ref: src/ve.py#activate
  implements: CLI handler for task-aware chunk activation
- ref: src/ve.py#overlap
  implements: CLI handler for task-aware overlap detection
- ref: tests/test_task_context_cmds.py
  implements: Integration tests for task-aware activate and overlap commands
narrative: null
investigation: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
friction_entries:
- entry_id: F002
  scope: full
bug_type: semantic
created_after:
- bug_type_field
- cluster_subsystem_prompt
---

# Chunk Goal

## Minor Goal

Extend task-context awareness to `ve chunk overlap`, `ve chunk validate`, and
`ve chunk activate` commands. Currently, these commands only operate within a
single project context, but in task context (multi-project workflows), they need
to understand and traverse project-qualified references.

This work closes a semantic gap in the task-context implementation. The
`cross_repo_chunks` narrative established task-awareness for creation and listing
commands but did not address operational commands. F002 documents real user
friction where validation used the wrong context.

**Intended behaviors:**

- **overlap**: When computing overlap for a chunk created in task context:
  - Resolve project-qualified code references (e.g., `project_name::src/foo.py#Bar`)
    and verify them in the target project
  - Compute overlap against ALL chunks in scope: both task-level chunks (in
    artifact-only directories) AND project-level chunks (across all projects in
    the task)
  - This enables detecting when a task-context chunk touches code that a
    project-level chunk also governs

- **validate**: When run from task context:
  - Verify project-qualified references resolve correctly to their target projects
  - Validate cross-project external chunk references
  - When run from a project directory within a task, respect that project's
    context but still resolve cross-project references via task context

- **activate**: Should work correctly when activating a chunk in any project
  within the task, respecting the project-qualified chunk location.

## Success Criteria

- `ve chunk overlap <chunk>` resolves project-qualified code references and
  verifies them in the target project
- `ve chunk overlap` computes overlap against both task-level chunks (artifact-only)
  AND project-level chunks (across all projects in task)
- `ve chunk validate` verifies project-qualified references when run from task context
- `ve chunk validate` respects project context when run from within a project,
  while still resolving cross-project references via task context
- `ve chunk activate` works for chunks in any project within a task
- Existing single-project behavior remains unchanged (backward compatible)
- Hard Invariant #11 in `workflow_artifacts` subsystem is extended or a new
  invariant is added to document task-context requirements for operational commands
- Tests cover task-context scenarios for all three commands

