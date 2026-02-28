---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/review_routing.py
- tests/test_orchestrator_review_routing.py
code_references:
- ref: src/orchestrator/review_routing.py#route_review_decision
  implements: "Max iterations check moved to FEEDBACK-only path so APPROVE always succeeds"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- dead_code_removal
- narrative_compact_extract
- persist_retry_state
- repo_cache_dry
- reviewer_decisions_dedup
- worktree_merge_extract
- phase_aware_recovery
---

# Chunk Goal

## Minor Goal

Fix a bug in `route_review_decision()` where the max review iterations check fires unconditionally, regardless of the review decision. Currently, when `review_iterations + 1 > max_iterations`, the function immediately escalates to NEEDS_ATTENTION and returns — even when the reviewer returned APPROVE. This creates an infinite loop: the reviewer approves, the routing layer escalates anyway, the operator answers the attention item, the review runs again, approves again, escalates again.

The fix: move the iteration limit check so it only applies when the review decision is **not** APPROVE. If the reviewer approves, the chunk should advance to COMPLETE regardless of how many review iterations occurred.

## Success Criteria

- In `src/orchestrator/review_routing.py`, the max iterations check in `route_review_decision()` no longer fires when the parsed review decision is APPROVE
- A review that returns APPROVE after 4+ iterations advances to COMPLETE instead of escalating to NEEDS_ATTENTION
- A review that returns FEEDBACK still escalates to NEEDS_ATTENTION when iterations exceed `max_iterations`
- Existing tests updated or new tests added to cover the approve-after-max-iterations path
- All existing tests pass