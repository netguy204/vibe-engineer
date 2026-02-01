---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/api.py
- tests/test_orchestrator_api.py
code_references:
  - ref: src/orchestrator/api.py#inject_endpoint
    implements: "Filters already-DONE blockers from blocked_by before determining initial status"
  - ref: tests/test_orchestrator_api.py#TestInjectFiltersDoneBlockers
    implements: "Test suite for DONE blocker filtering during injection"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- reviewer_decisions_nudge
---

# Chunk Goal

## Minor Goal

Fix the orchestrator inject endpoint to filter out already-DONE chunks from `blocked_by` before setting the initial work unit status. Currently, when a work unit is injected with `blocked_by=["chunk_x"]` and `chunk_x` is already DONE, the work unit is created with status=BLOCKED and never gets unblocked.

**Root cause**: In `src/orchestrator/api.py#inject_endpoint`, the logic is:
```python
initial_status = WorkUnitStatus.BLOCKED if blocked_by else WorkUnitStatus.READY
```

This doesn't check if the blocking chunks are already DONE. The `unblock_dependents()` function only runs when something **transitions** to DONE, so if a blocker was already DONE before the dependent was injected, there's no mechanism to unblock it.

**Related**: This is distinct from F020 (`orch_manual_done_unblock`) which handles the case where work units already exist and then their blocker is manually marked DONE. This bug is about new work units injected with blockers that are already DONE.

## Success Criteria

- `inject_endpoint` filters `blocked_by` to remove chunks that are already DONE before determining initial status
- Work units injected with only already-DONE blockers start as READY, not BLOCKED
- Work units injected with a mix of DONE and non-DONE blockers start as BLOCKED with only non-DONE chunks in `blocked_by`
- Test case: inject a chunk with `blocked_by=["done_chunk"]` where `done_chunk` is DONE → starts as READY
- Test case: inject a chunk with `blocked_by=["done_chunk", "pending_chunk"]` → starts as BLOCKED with `blocked_by=["pending_chunk"]`
- Existing injection behavior for non-DONE blockers is unchanged