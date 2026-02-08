---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/worktree.py
  - src/orchestrator/scheduler.py
  - src/orchestrator/api.py
  - tests/test_orchestrator_worktree.py
code_references:
  - ref: src/orchestrator/worktree.py#WorktreeManager::finalize_work_unit
    implements: "Consolidated worktree finalization logic (commit, remove, merge, cleanup)"
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "Uses finalize_work_unit for work unit completion"
  - ref: src/orchestrator/api.py#prune_work_unit_endpoint
    implements: "Single worktree prune using finalize_work_unit"
  - ref: src/orchestrator/api.py#prune_all_endpoint
    implements: "Batch worktree prune using finalize_work_unit"
  - ref: tests/test_orchestrator_worktree.py#TestFinalizeWorkUnit
    implements: "Unit tests for finalize_work_unit method"
  - ref: src/orchestrator/api/worktrees.py
    implements: "Consolidated worktree finalization in prune endpoint"
narrative: arch_consolidation
investigation: null
subsystems:
  - subsystem_id: orchestrator
    relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Extract and consolidate the duplicated worktree prune/merge/cleanup logic from scheduler.py and api.py into a single source of truth in worktree.py. This eliminates three copies of the same 50-line sequence (commit uncommitted changes, remove worktree, check for changes, merge to base, cleanup empty branches) that currently risks logic drift and maintenance burden.

This is a pure refactoring with no behavioral changes - all three call sites will delegate to the new consolidated method.

## Success Criteria

- New method `finalize_work_unit(chunk: str) -> None` exists in worktree.py containing the consolidated logic
- Method handles both success case (merge and cleanup) and failure case (error handling with WorktreeError)
- All three call sites (scheduler._advance_phase, api.prune_work_unit_endpoint, api.prune_all_endpoint) replaced with calls to the new method
- Existing orchestrator tests pass without modification (behavior unchanged)
- No logic drift between the three original implementations - consolidated version preserves all edge case handling (uncommitted changes, empty branches, missing worktrees, merge conflicts)

