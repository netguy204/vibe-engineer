---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/task_utils.py
- tests/test_task_chunk_list.py
code_references:
- ref: src/task_utils.py#list_task_chunks
  implements: List chunks from external repo with status and dependents
- ref: src/task_utils.py#get_current_task_chunk
  implements: Get current IMPLEMENTING chunk from external repo
- ref: src/ve.py#list_chunks
  implements: CLI command with task directory detection
- ref: src/ve.py#_list_task_chunks
  implements: Task-aware chunk listing output handler
narrative: cross_repo_chunks
subsystems: []
created_after:
- proposed_chunks_frontmatter
---

# Chunk Goal

## Minor Goal

Extend `ve chunk list` to detect task directory context and list chunks from the external chunk repository. This is the fifth chunk in the cross-repo narrative, building on the infrastructure from chunks 7-10.

When working in a task directory (detected by `.ve-task.yaml`), the current `ve chunk list` behavior doesn't make sense - there's no `docs/chunks/` in the task directory itself. Instead, the command should operate on the external chunk repository, showing all chunks with their dependent repos.

This directly advances docs/trunk/GOAL.md's required property: "It must be possible to perform the workflow outside the context of a Git repository."

## Success Criteria

### 1. Task Directory Detection

When `ve chunk list` runs:
- If in a task directory (`.ve-task.yaml` exists), operate in task-aware mode
- Otherwise, use existing single-repo behavior unchanged

### 2. Task-Aware List Output

When in a task directory, `ve chunk list` should:
- List chunks from the **external chunk repository** (not the task directory or projects)
- For each chunk, show the `dependents` repos from the chunk's GOAL.md frontmatter
- Output format shows the chunk and its dependent projects

Example output when run from a task directory:
```
docs/chunks/0002-auth_validation [IMPLEMENTING]
  dependents: acme/service-a (0005), acme/service-b (0009)
docs/chunks/0001-auth_token [ACTIVE]
  dependents: acme/service-a (0003), acme/service-b (0007)
```

### 3. Task-Aware --latest Flag

When `--latest` is used in a task directory:
- Return the highest IMPLEMENTING chunk from the **external chunk repository**
- Output format: `docs/chunks/{chunk_name}`

This allows commands like `$(ve chunk list --latest)` to work correctly in task context.

### 4. Preserved Single-Repo Behavior

When not in a task directory (using `--project-dir` or current directory):
- Behavior is identical to current implementation
- No dependents are shown (single-repo chunks don't have them)

### 5. Error Handling

- If in task directory but external repo not accessible: clear error message
- If external repo has no chunks: "No chunks found" error (same as current)
- If `--latest` but no IMPLEMENTING chunk in external repo: "No implementing chunk found" error

### 6. Tests

- Task-aware list shows external repo chunks with dependents
- Task-aware `--latest` returns external repo's implementing chunk
- Single-repo behavior unchanged (existing tests pass)
- Error cases: missing external repo, no chunks, no implementing chunk