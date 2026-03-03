---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/scheduler.py
  - tests/test_orchestrator_scheduler_unblock.py
code_references:
  - ref: src/orchestrator/scheduler.py#Scheduler::_unblock_dependents
    implements: "Fix NEEDS_ATTENTION to READY transition when blockers complete"
  - ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
    implements: "Clear attention_reason and blocked_by when transitioning to RUNNING"
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "Clear attention_reason when transitioning to READY on phase advancement"
  - ref: tests/test_orchestrator_scheduler_unblock.py#TestNeedsAttentionUnblock
    implements: "Tests for NEEDS_ATTENTION to READY transition on unblock"
  - ref: tests/test_orchestrator_scheduler_unblock.py#TestAttentionReasonCleanup
    implements: "Tests for attention_reason and blocked_by cleanup on status transitions"
narrative: null
investigation: null
subsystems: []
friction_entries:
- entry_id: F001
  scope: full
created_after:
- artifact_copy_backref
- friction_claude_docs
- friction_template_and_cli
- orch_conflict_template_fix
- orch_sandbox_enforcement
- orch_blocked_lifecycle
---

# Chunk Goal

## Minor Goal

Fix the orchestrator scheduler bug where work units remain stuck in NEEDS_ATTENTION
status after their blocking work units complete. When a blocker completes and is
removed from a work unit's `blocked_by` list, if that list becomes empty, the work
unit should automatically transition from NEEDS_ATTENTION back to READY status.

Currently, the scheduler correctly clears the `blocked_by` list but fails to update
the status, leaving work units orphaned in NEEDS_ATTENTION with stale attention
reasons. This requires manual intervention via `ve orch work-unit status <chunk> READY`.

## Success Criteria

- When a work unit's last blocker completes, the work unit transitions from
  NEEDS_ATTENTION to READY automatically (no manual intervention required)
- The `attention_reason` field is cleared on ANY transition to READY or RUNNING
  (not just unblock scenarios - also manual status changes, retries, etc.)
- The `blocked_by` list is cleared when a work unit transitions to RUNNING
  (currently RUNNING work units still show stale blockers in `ve orch ps`)
- `ve orch ps` output shows no stale reasons or blockers for active work units
- Test coverage for the unblock-to-ready transition path
- Test coverage for reason and blocked_by cleanup on status transitions
- Existing orchestrator tests continue to pass

## Investigation Context

This bug was discovered during `/orchestrator-investigate` when three work units
(`friction_chunk_linking`, `selective_project_linking`, `remove_external_ref`)
were stuck in NEEDS_ATTENTION after their blocker `artifact_copy_backref` completed.

**Observed behavior from logs:**
```
Removed artifact_copy_backref from friction_chunk_linking's blocked_by (remaining: [])
Removed artifact_copy_backref from selective_project_linking's blocked_by (remaining: [])
Removed artifact_copy_backref from remove_external_ref's blocked_by (remaining: [])
```

The `blocked_by` lists were correctly cleared, but the work units remained stuck
with status=NEEDS_ATTENTION and stale attention_reason messages still referencing
`artifact_copy_backref`.

**Likely fix location:** The scheduler code that handles blocker completion
(look for "Removed X from Y's blocked_by" log message) needs to check if
`blocked_by` is now empty and, if so, transition status to READY and clear
`attention_reason`.

**Related issue #1:** The `attention_reason` field persists when work units are
manually reset to READY or when they transition to RUNNING. This causes confusing
output in `ve orch ps` where work units show reasons that no longer apply. The fix
should clear `attention_reason` on any transition to READY or RUNNING.

**Related issue #2:** The `blocked_by` list is not cleared when work units transition
to RUNNING. Observed: `remove_external_ref` was RUNNING but still showed
`friction_chunk_linking` in its BLOCKED BY column even though that chunk was DONE.
The `blocked_by` list should be cleared when a work unit starts running.