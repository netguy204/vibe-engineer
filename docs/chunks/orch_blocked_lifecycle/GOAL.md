---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/api/conflicts.py
  - src/orchestrator/scheduler.py
  - src/orchestrator/state.py
  - tests/test_orchestrator_api.py
  - tests/test_orchestrator_scheduler_unblock.py
code_references:
  - ref: src/orchestrator/api/conflicts.py#resolve_conflict_endpoint
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
  - ref: tests/test_orchestrator_scheduler_unblock.py#TestAutomaticUnblock
    implements: "Unit tests for automatic unblocking when blockers complete"
  - ref: tests/test_orchestrator_state.py#TestListBlockedByChunk
    implements: "Unit tests for list_blocked_by_chunk query method"
  - ref: src/orchestrator/api/conflicts.py
    implements: "SERIALIZE verdict transitions to BLOCKED and clears attention_reason"
narrative: null
investigation: null
subsystems: []
created_after: ["orch_mechanical_commit"]
---

# Chunk Goal

## Minor Goal

The orchestrator's conflict resolution system supports a complete blocked
lifecycle for serialized work units:

**SERIALIZE verdict transitions to BLOCKED**

When `ve orch resolve <chunk> --with <other> serialize` is called, the
`resolve_conflict_endpoint` adds the other chunk to `blocked_by`, transitions
status from `NEEDS_ATTENTION` to `BLOCKED`, and clears the `attention_reason`
field so the resolved conflict no longer surfaces as a stale reason.

**Automatic unblock when blockers complete**

When a work unit transitions to `DONE`, the scheduler scans for work units
with that chunk in their `blocked_by` list and removes the completed chunk.
If removal leaves `blocked_by` empty and the unit is `BLOCKED` or
`NEEDS_ATTENTION`, the unit transitions to `READY` and is picked up by the
next dispatch cycle.

Together these behaviors enable the workflow: resolve a conflict with SERIALIZE
→ work unit becomes BLOCKED → blocker completes → work unit automatically
becomes READY and resumes.

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

