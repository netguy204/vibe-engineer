---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/api/scheduling.py
- tests/test_orchestrator_api.py
code_references:
  - ref: src/orchestrator/api/scheduling.py#inject_endpoint
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

The orchestrator inject endpoint filters already-DONE chunks out of `blocked_by` before determining the initial work unit status. A work unit injected with `blocked_by=["chunk_x"]` where `chunk_x` is already DONE starts as READY rather than BLOCKED, since `unblock_dependents()` only runs on a transition **to** DONE and would never fire for blockers that completed before the dependent was injected.

The filter handles the inject path specifically. The case of work units already existing when their blocker is manually marked DONE is owned by `orch_manual_done_unblock` (F020); this chunk owns the new-injection case.

## Success Criteria

- `inject_endpoint` filters `blocked_by` to remove chunks that are already DONE before determining initial status
- Work units injected with only already-DONE blockers start as READY, not BLOCKED
- Work units injected with a mix of DONE and non-DONE blockers start as BLOCKED with only non-DONE chunks in `blocked_by`
- Test case: inject a chunk with `blocked_by=["done_chunk"]` where `done_chunk` is DONE → starts as READY
- Test case: inject a chunk with `blocked_by=["done_chunk", "pending_chunk"]` → starts as BLOCKED with `blocked_by=["pending_chunk"]`
- Existing injection behavior for non-DONE blockers is unchanged