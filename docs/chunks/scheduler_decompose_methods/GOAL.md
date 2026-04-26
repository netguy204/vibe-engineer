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

The orchestrator scheduler keeps two previously oversized concerns in dedicated locations:

(a) Phase progression in `src/orchestrator/scheduler.py#Scheduler._advance_phase` is focused on advancing a work unit to its next phase. Completion/cleanup logic (status verification, mechanical commits, displaced chunk restoration, finalize/merge/cleanup, DONE transition) lives in `Scheduler._finalize_completed_work_unit()`.

(b) Review decision routing — the three-priority fallback chain for review decision parsing, nudge logic, loop detection, and APPROVE/FEEDBACK/ESCALATE routing — lives in `src/orchestrator/review_routing.py` alongside the existing `review_parsing.py`. The scheduler interacts with it via a thin `_handle_review_result` wrapper and a `_SchedulerReviewCallbacks` adapter implementing the `ReviewRoutingCallbacks` protocol.

This decomposition extends the pattern established by the earlier extraction of `activation.py`, `retry.py`, and `review_parsing.py`.

## Success Criteria

- `_advance_phase` is under 80 lines, focused on phase progression logic
- Completion/cleanup logic lives in `_finalize_completed_work_unit()` or similar well-named method
- Review routing logic lives in `src/orchestrator/review_routing.py`
- `review_routing.py` is testable in isolation without scheduler dependencies
- No behavioral changes — all existing orchestrator tests pass
- `scheduler.py` is reduced by at least 200 lines

