---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- src/orchestrator/review_routing.py
- tests/test_orchestrator_review_routing.py
code_references:
  - ref: src/orchestrator/scheduler.py#Scheduler::_finalize_completed_work_unit
    implements: "Extracted completion/cleanup logic from _advance_phase"
  - ref: src/orchestrator/scheduler.py#_SchedulerReviewCallbacks
    implements: "Adapter implementing ReviewRoutingCallbacks protocol for scheduler integration"
  - ref: src/orchestrator/scheduler.py#Scheduler::_handle_review_result
    implements: "Thin wrapper delegating to review_routing module"
  - ref: src/orchestrator/review_routing.py#ReviewRoutingConfig
    implements: "Configuration dataclass for review routing settings"
  - ref: src/orchestrator/review_routing.py#ReviewRoutingCallbacks
    implements: "Protocol defining callbacks for review routing to interact with scheduler"
  - ref: src/orchestrator/review_routing.py#route_review_decision
    implements: "Main review routing function with three-priority fallback chain"
  - ref: src/orchestrator/review_routing.py#_apply_review_decision
    implements: "APPROVE/FEEDBACK/ESCALATE routing logic"
  - ref: tests/test_orchestrator_review_routing.py
    implements: "Isolated tests for review_routing module"
narrative: arch_review_remediation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- model_package_cleanup
- orchestrator_api_decompose
- task_operations_decompose
---

# Chunk Goal

## Minor Goal

This chunk decomposes two oversized methods in the orchestrator scheduler:

(a) `_advance_phase` in `src/orchestrator/scheduler.py` (around lines 562-753) is a 190-line God Method that handles both "advance to next phase" and "work unit is finished, clean up." The completion/cleanup logic (status verification, mechanical commits, displaced chunk restoration, finalize/merge/cleanup, DONE transition) should be extracted into a `_finalize_completed_work_unit()` method, leaving `_advance_phase` focused on phase progression.

(b) `_handle_review_result` (around lines 925-1135) is 160 lines implementing a three-priority fallback chain for review decision parsing, nudge logic, loop detection, and APPROVE/FEEDBACK/ESCALATE routing. This is a self-contained sub-state-machine that should be extracted into a `review_routing.py` module alongside the existing `review_parsing.py`.

A prior `scheduler_decompose` chunk already extracted `activation.py`, `retry.py`, and `review_parsing.py` — this chunk continues that decomposition for the two remaining oversized methods.

## Success Criteria

- `_advance_phase` is under 80 lines, focused on phase progression logic
- Completion/cleanup logic lives in `_finalize_completed_work_unit()` or similar well-named method
- Review routing logic lives in `src/orchestrator/review_routing.py`
- `review_routing.py` is testable in isolation without scheduler dependencies
- No behavioral changes — all existing orchestrator tests pass
- `scheduler.py` is reduced by at least 200 lines

