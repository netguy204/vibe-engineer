---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- src/orchestrator/activation.py
- tests/test_orchestrator_phase_recovery.py
code_references:
  - ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
    implements: "Phase-aware activation check - only calls activate_chunk_in_worktree during PLAN phase"
  - ref: src/orchestrator/scheduler.py#Scheduler::_recover_from_crash
    implements: "Worktree preservation during crash recovery - preserves worktree reference if directory still exists"
  - ref: src/orchestrator/worktree.py#WorktreeManager::worktree_exists
    implements: "Worktree existence check for crash recovery decision logic"
  - ref: tests/test_orchestrator_phase_recovery.py#TestPhaseAwareActivation
    implements: "Tests verifying activation only called during PLAN phase"
  - ref: tests/test_orchestrator_phase_recovery.py#TestWorktreePreservationInRecovery
    implements: "Tests for worktree preservation during crash recovery"
  - ref: tests/test_orchestrator_phase_recovery.py#TestCrashRecoveryAtEachPhase
    implements: "Integration tests for crash recovery at each phase"
narrative: arch_review_gaps
investigation: null
subsystems:
  - subsystem_id: orchestrator
    relationship: implements
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- dev_tooling_infra
- dispatch_toctou_guard
- finalization_recovery
---

# Chunk Goal

## Minor Goal

Orchestrator crash recovery is phase-aware so that restarting the daemon
correctly resumes work units at any phase, not just PLAN.

`_recover_from_crash()` in `src/orchestrator/scheduler.py` preserves a work
unit's worktree reference when the worktree directory still exists on disk,
rather than unconditionally clearing it. When the scheduler re-dispatches a
recovered unit, `_run_work_unit()` only invokes
`activate_chunk_in_worktree()` during the PLAN phase. For every subsequent
phase, the chunk has already moved past FUTURE on the branch, so activation
is skipped:

- **PLAN**: Chunk is FUTURE on main. Fresh worktree + activation runs.
- **IMPLEMENT**: Chunk is IMPLEMENTING (from PLAN phase). Activation is
  skipped; the existing branch state is correct.
- **REBASE / REVIEW**: Chunk is IMPLEMENTING on the branch. Activation is
  skipped.
- **COMPLETE**: Chunk is ACTIVE or HISTORICAL (set by the COMPLETE agent).
  Activation is skipped — calling it here would fail with "expected
  'FUTURE' for activation" and force NEEDS_ATTENTION.

Worktree creation itself remains safe across re-dispatch: `_create_branch`
skips if the `orch/<chunk>` branch exists, and `_create_single_repo_worktree`
returns early if the worktree directory is present. The phase gate on
activation is what makes restarts at any phase succeed; for PLAN, activation
performs the FUTURE → IMPLEMENTING transition, and for all other phases the
worktree just needs to exist with the branch checked out.

## Success Criteria

- `_run_work_unit()` only calls `activate_chunk_in_worktree()` during the
  PLAN phase. For IMPLEMENT, REBASE, REVIEW, and COMPLETE phases, the
  worktree is created (or reused) but activation is skipped.
- `_recover_from_crash()` preserves the worktree path on the work unit if
  the worktree directory still exists on disk, rather than unconditionally
  clearing it. This avoids needless worktree recreation.
- A daemon restart during any phase (PLAN, IMPLEMENT, REBASE, REVIEW,
  COMPLETE) results in the work unit being re-dispatched and completing
  successfully, without hitting NEEDS_ATTENTION due to activation failure.
- Test coverage for crash recovery at each phase: PLAN (chunk is FUTURE),
  IMPLEMENT (chunk is IMPLEMENTING), COMPLETE (chunk is ACTIVE or
  HISTORICAL).
- All existing orchestrator tests continue to pass.

## Rejected Ideas

### Make `activate_chunk_in_worktree` accept all post-IMPLEMENTING statuses

We could broaden the activation function to accept ACTIVE, HISTORICAL, etc.
in addition to FUTURE and IMPLEMENTING. This would make the COMPLETE phase
work, but it would mask the real problem: activation is a PLAN-phase
concept that shouldn't be called during other phases. Broadening it would
hide the semantic mismatch rather than fixing it, and would not correctly
handle the displaced chunk tracking that activation manages (displaced
chunks are only relevant at the start of the PLAN phase).