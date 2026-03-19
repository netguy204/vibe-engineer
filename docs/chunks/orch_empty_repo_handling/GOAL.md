---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/git_utils.py
- src/orchestrator/daemon.py
code_references:
  - ref: src/orchestrator/git_utils.py#repo_has_commits
    implements: "Check whether a git repo has any commits"
  - ref: src/orchestrator/git_utils.py#get_current_branch
    implements: "Improved error message for empty repo case"
  - ref: src/orchestrator/daemon.py#start_daemon
    implements: "Early guard against empty repos before daemon fork"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- entity_memory_decay
- entity_memory_schema
- entity_shutdown_skill
- entity_startup_skill
- entity_touch_command
- orch_retry_single
---

# Chunk Goal

## Minor Goal

Handle the case where the orchestrator is started in a git repo with no commits.

The orchestrator calls `git rev-parse HEAD` (or similar) to determine the base branch for worktree creation. In a fresh repo with no commits, HEAD doesn't exist, causing: `Could not determine base branch: Failed to get current branch: fatal: ambiguous argument HEAD: unknown revision or path not in the working tree.`

The fix should either:
- Provide a clear error message telling the user to make an initial commit first, OR
- Default to the repo's configured init branch name (e.g., `git config init.defaultBranch` or fallback to `main`)

Reported by an external steward attempting to bootstrap a new project.

## Success Criteria

- `ve orch start` in a repo with no commits produces a clear, actionable error message
- The error message suggests making an initial commit
- No stack trace or git internals exposed to the user
- Tests verify the error path for repos with no commits

