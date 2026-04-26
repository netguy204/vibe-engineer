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

The orchestrator always injects a user prompt when re-entering the IMPLEMENT phase from any transition, and enforces an iteration limit so chunks cannot cycle unboundedly.

Every re-entry to IMPLEMENT carries a contextual user prompt explaining why the chunk was sent back. Review FEEDBACK supplies the specific reviewer issues (the `orch_review_feedback_fidelity` mechanism); rebase conflicts and test failures supply the conflict files and test output; any other transition supplies its own reason. The implementer never wakes up with only a SystemMessage init and no task.

The work unit tracks `implement_iterations` — the total number of IMPLEMENT phase dispatches — and `reentry_context` — the context string the scheduler hands to the agent on the next dispatch. The scheduler increments `implement_iterations` on every IMPLEMENT run and clears `reentry_context` once it has been consumed. APPROVE in the review router resets `implement_iterations` to 0.

The reviewer's `max_iterations` (loaded from reviewer config) is the hard ceiling for the entire review-implement loop, not just the reviewer's internal counter. Once `implement_iterations` exceeds `max_iterations`, the scheduler escalates the work unit to NEEDS_ATTENTION rather than dispatching IMPLEMENT again.

## Success Criteria

- Implementer receives a contextual user prompt on EVERY re-entry to IMPLEMENT phase
- Rebase failure re-entry includes conflict files and/or test failure output
- Work unit tracks implement iteration count
- Orchestrator escalates to NEEDS_ATTENTION after max_iterations round-trips
- No unbounded cycling: a chunk cannot run IMPLEMENT more than max_iterations + 1 times
- Tests verify: re-entry prompt content for each transition path, iteration limit enforcement

