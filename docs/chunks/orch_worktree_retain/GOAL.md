---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- src/orchestrator/worktree.py
- src/orchestrator/models.py
- src/orchestrator/api/scheduling.py
- src/orchestrator/api/worktrees.py
- src/cli/orch.py
- src/orchestrator/templates/dashboard.html
- tests/test_orchestrator_worktree.py
- tests/test_orchestrator_scheduler.py
- docs/trunk/ORCHESTRATOR.md
code_references:
- ref: src/orchestrator/models.py#WorkUnit
  implements: Work unit model with retain_worktree field for worktree retention
- ref: src/orchestrator/models.py#OrchestratorConfig
  implements: Config model with worktree_warning_threshold field
- ref: src/orchestrator/models.py#WorktreeInfo
  implements: Data model for worktree listing with status information
- ref: src/orchestrator/scheduler.py#Scheduler::_recover_from_crash
  implements: Orphan recovery that preserves worktrees instead of deleting them
- ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
  implements: Worktree retention logic on completion based on retain_worktree flag
- ref: src/orchestrator/api/scheduling.py#inject_endpoint
  implements: API endpoint with retain_worktree parameter support
- ref: src/orchestrator/api/worktrees.py#list_worktrees_endpoint
  implements: GET /worktrees endpoint returning worktree status information
- ref: src/orchestrator/api/worktrees.py#remove_worktree_endpoint
  implements: DELETE /worktrees/{chunk} endpoint for explicit worktree removal
- ref: src/orchestrator/api/worktrees.py#prune_work_unit_endpoint
  implements: POST /work-units/{chunk}/prune for merging and cleaning retained worktree
- ref: src/orchestrator/api/worktrees.py#prune_all_endpoint
  implements: POST /work-units/prune for batch cleanup of retained worktrees
- ref: src/cli/orch.py#worktree
  implements: CLI subgroup for worktree management commands
- ref: src/cli/orch.py#worktree_list
  implements: CLI command to list worktrees with status
- ref: src/cli/orch.py#worktree_remove
  implements: CLI command to remove worktree without merging
- ref: src/cli/orch.py#worktree_prune
  implements: CLI command to prune all retained worktrees
- ref: src/cli/orch.py#orch_prune
  implements: CLI command to prune specific or all retained worktrees
- ref: src/cli/orch.py#orch_inject
  implements: CLI inject command with --retain flag support
- ref: src/orchestrator/api/worktrees.py
  implements: "Worktree management endpoints (list, remove, prune, batch prune)"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- cli_modularize
created_after:
- cli_modularize
- reviewer_decisions_nudge
---

# Chunk Goal

## Minor Goal

Retain worktrees after work unit completion until explicitly removed by user action. Currently, the orchestrator automatically deletes worktrees in two scenarios that can cause data loss:

1. **After successful completion**: Worktrees are removed immediately after merge in `_handle_completion()`
2. **During orphan recovery**: When the daemon restarts and finds orphaned RUNNING work units, it deletes their worktrees in `_recover_from_crash()`

The second case caused a critical data loss incident where `cli_modularize` had ~20 minutes of implementation work (creating `src/cli/` with 11 module files, refactoring 4,500 lines) that was lost when the COMPLETE phase got orphaned and the worktree was deleted on recovery.

This chunk changes worktree lifecycle to require explicit user action for removal, providing a safety net for recovering work from failed or orphaned phases.

## Success Criteria

- Worktrees are NOT automatically deleted after successful work unit completion
- Worktrees are NOT automatically deleted during orphan recovery (`_recover_from_crash`)
- New CLI command `ve orch worktree remove <chunk>` allows explicit worktree removal
- New CLI command `ve orch worktree list` shows all retained worktrees with their status (completed, orphaned, active)
- Dashboard shows worktree retention status and provides removal action
- `ve orch worktree prune` command removes all worktrees for COMPLETED work units (batch cleanup)
- Warning is logged when worktree count exceeds configurable threshold (default: 10)
- Documentation updated to explain worktree retention behavior and cleanup workflow