---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/api.py
  - src/orchestrator/scheduler.py
  - src/orchestrator/state.py
  - tests/test_orchestrator_api.py
  - tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/api.py#resolve_conflict_endpoint
    implements: "Bug 1 fix: SERIALIZE verdict transitions status to BLOCKED and clears attention_reason"
  - ref: src/orchestrator/scheduler.py#Scheduler::_unblock_dependents
    implements: "Bug 2 fix: Automatic unblock when blockers complete"
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "Calls _unblock_dependents after work unit transitions to DONE"
  - ref: src/orchestrator/state.py#StateStore::list_blocked_by_chunk
    implements: "Query for work units blocked by a specific chunk"
  - ref: tests/test_orchestrator_api.py#TestResolveConflictEndpoint
    implements: "Unit tests for SERIALIZE status transition and attention_reason clearing"
  - ref: tests/test_orchestrator_api.py#TestBlockedLifecycleIntegration
    implements: "Integration test for full blocked lifecycle flow"
  - ref: tests/test_orchestrator_scheduler.py#TestAutomaticUnblock
    implements: "Unit tests for automatic unblocking when blockers complete"
  - ref: tests/test_orchestrator_state.py#TestListBlockedByChunk
    implements: "Unit tests for list_blocked_by_chunk query method"
narrative: null
investigation: null
subsystems: []
created_after: ["orch_mechanical_commit"]
---

# Chunk Goal

## Minor Goal

The orchestrator's conflict resolution system has two deficiencies that prevent
serialized work units from automatically resuming after their blockers complete:

**Bug 1: Status not updated on SERIALIZE verdict**

When `ve orch resolve <chunk> --with <other> serialize` is called, the endpoint
at `src/orchestrator/api.py:777-780` correctly adds the other chunk to
`blocked_by`, but fails to:
- Transition status from `NEEDS_ATTENTION` to `BLOCKED`
- Clear the `attention_reason` field

This leaves the work unit stuck in `NEEDS_ATTENTION` with a stale attention
reason even though the conflict has been resolved.

**Bug 2: No automatic unblock when blockers complete**

When a work unit transitions to `DONE` status, there is no logic to check if
other work units were blocked by it and should now be unblocked. Work units
with `status=BLOCKED` and `blocked_by=[completed_chunk]` remain blocked forever
unless manually transitioned to `READY`.

This chunk fixes both issues to enable the expected workflow: resolve a conflict
with SERIALIZE → work unit becomes BLOCKED → blocker completes → work unit
automatically becomes READY and resumes.

## Success Criteria

**Bug 1 fix (resolve endpoint):**
- When SERIALIZE verdict is given via `resolve_conflict_endpoint`, the work unit
  status transitions from `NEEDS_ATTENTION` to `BLOCKED`
- The `attention_reason` field is cleared
- The `blocked_by` list contains the serialized-after chunk (existing behavior)

**Bug 2 fix (automatic unblock):**
- When a work unit transitions to `DONE`, any work units with that chunk in their
  `blocked_by` list have it removed
- If removal leaves `blocked_by` empty and status is `BLOCKED`, status transitions
  to `READY`
- The unblocked work unit is picked up by the scheduler on the next dispatch cycle

**Testing:**
- Unit test: SERIALIZE resolution updates status to BLOCKED and clears attention_reason
- Unit test: Completing a work unit unblocks dependents
- Integration test: Full lifecycle - inject two chunks, serialize one after the
  other, complete the first, verify the second automatically starts

