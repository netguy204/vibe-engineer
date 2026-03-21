---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/models.py
- src/orchestrator/agent.py
- src/orchestrator/scheduler.py
- src/orchestrator/review_routing.py
- src/orchestrator/state.py
- tests/test_orchestrator_reentry.py
code_references:
- ref: src/orchestrator/models.py#WorkUnit::implement_iterations
  implements: "Track total IMPLEMENT phase dispatches on work unit"
- ref: src/orchestrator/models.py#WorkUnit::reentry_context
  implements: "Store re-entry context string for IMPLEMENT phase injection"
- ref: src/orchestrator/agent.py#AgentRunner::run_phase
  implements: "Inject reentry_context into IMPLEMENT prompt with Re-entry Context header"
- ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
  implements: "Increment implement_iterations, enforce max_iterations limit, pass reentry_context to agent"
- ref: src/orchestrator/review_routing.py#_apply_review_decision
  implements: "Reset implement_iterations to 0 on APPROVE"
- ref: src/orchestrator/state.py#StateStore::_migrate_v16
  implements: "Database migration adding implement_iterations and reentry_context columns"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- orch_review_feedback_fidelity
---

# Chunk Goal

## Minor Goal

Ensure the orchestrator ALWAYS injects a user prompt when re-entering the IMPLEMENT phase from any transition, and enforce an iteration limit to prevent unbounded cycling.

**Root cause**: The implement phase receives NO user prompt on re-entry from ANY transition path — not just review FEEDBACK (fixed in `orch_review_feedback_fidelity`), but also rebase failures and test failures. The implementer wakes up with only a SystemMessage init and no task, guesses what to do, does busywork, and exits. This cycles indefinitely because the orchestrator also does not enforce the reviewer's `max_iterations` limit.

Evidence: `canvas_chat_interface` went through 7 implement cycles with 0 user prompts on runs 2-7, costing $3.97+ in inference doing random cleanup instead of addressing specific issues.

Three fixes needed:

1. **Every re-entry to IMPLEMENT must include a user prompt** explaining WHY the chunk was sent back:
   - From review FEEDBACK: specific issues (already handled by `orch_review_feedback_fidelity`)
   - From rebase conflict/failure: the conflict files and test failure output
   - From any other transition: the reason for re-entry

2. **Track implement iteration count** on the work unit (e.g., `implement_iteration` field) so the orchestrator knows how many times IMPLEMENT has run.

3. **Enforce max_iterations at the orchestrator level**: After N round-trips (configurable, default from reviewer config), escalate to NEEDS_ATTENTION rather than continuing to cycle. The reviewer's `max_iterations: 3` should be the hard ceiling for the entire review-implement loop, not just the reviewer's internal counter.

## Success Criteria

- Implementer receives a contextual user prompt on EVERY re-entry to IMPLEMENT phase
- Rebase failure re-entry includes conflict files and/or test failure output
- Work unit tracks implement iteration count
- Orchestrator escalates to NEEDS_ATTENTION after max_iterations round-trips
- No unbounded cycling: a chunk cannot run IMPLEMENT more than max_iterations + 1 times
- Tests verify: re-entry prompt content for each transition path, iteration limit enforcement

