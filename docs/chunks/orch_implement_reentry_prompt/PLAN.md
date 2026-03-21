


# Implementation Plan

## Approach

Three coordinated changes across the orchestrator to ensure every re-entry to IMPLEMENT includes a contextual prompt, track iteration count, and enforce a hard ceiling on implement cycles.

**Strategy**: Follow the pattern established by `orch_review_feedback_fidelity` — the FEEDBACK re-entry path already injects review feedback via `agent.py`'s `run_phase()`. We extend this injection point to cover ALL re-entry paths (rebase failure, unaddressed feedback reroute, operator answer after escalate). We also add an `implement_iterations` counter to WorkUnit (per DEC-008: Pydantic models for data contracts) and enforce `max_iterations` at the orchestrator level before dispatching IMPLEMENT, not just after review decisions.

**Key insight**: The existing `review_iterations` counter only increments after a REVIEW→FEEDBACK decision. But the implementer can cycle through IMPLEMENT multiple times without ever reaching review (e.g., unaddressed feedback reroute at scheduler line 721, or rebase failures cycling back to IMPLEMENT). We need a counter that increments on every IMPLEMENT dispatch, regardless of the path that got there.

**Build on**:
- `agent.py` line 564-578: existing REVIEW_FEEDBACK.md injection pattern
- `scheduler.py` line 712-731: unaddressed feedback reroute (currently sends back with no context)
- `review_routing.py` line 318-362: FEEDBACK routing (already creates REVIEW_FEEDBACK.md)
- `scheduler.py` line 1152-1232: merge conflict retry (cycles to REBASE, which may fail and re-enter IMPLEMENT)

Tests follow TESTING_PHILOSOPHY.md: TDD with semantic assertions verifying prompt content for each re-entry path and iteration limit enforcement.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS new scheduling behavior (iteration tracking, re-entry prompt injection). Will follow the existing patterns for WorkUnit field additions and scheduler dispatch logic.

## Sequence

### Step 1: Add `implement_iterations` field to WorkUnit

Add `implement_iterations: int = 0` to `WorkUnit` in `src/orchestrator/models.py`. Also add it to `model_dump_json_serializable()` for API/dashboard visibility.

This counter tracks total IMPLEMENT phase dispatches. Unlike `review_iterations` (which tracks IMPLEMENT→REVIEW cycles), this increments every time the work unit enters IMPLEMENT, regardless of the source transition.

Location: `src/orchestrator/models.py`

### Step 2: Write tests for re-entry prompt injection

Before implementing, write tests that verify:
1. When IMPLEMENT re-enters after unaddressed feedback (reroute from pre-review check), the prompt includes context explaining why ("REVIEW_FEEDBACK.md was not deleted — you must address all feedback items")
2. When IMPLEMENT re-enters from any path, the prompt includes the re-entry reason
3. The existing REVIEW_FEEDBACK.md injection (from `orch_review_feedback_fidelity`) continues to work unchanged

These tests will exercise the prompt-building logic in `agent.py`'s `run_phase()`.

Location: `tests/test_orchestrator_feedback_injection.py` (extend existing) or new test file

### Step 3: Add re-entry context injection to `run_phase()`

Extend `agent.py`'s `run_phase()` to accept an optional `reentry_context: Optional[str]` parameter. When provided, prepend it to the prompt with a clear header:

```
## Re-entry Context

You are re-entering the IMPLEMENT phase. Here is why:

{reentry_context}

Address the above before doing any other work.
```

This is injected AFTER the REVIEW_FEEDBACK.md content (if present) and BEFORE the CWD reminder, so the implementer sees: (1) feedback to address, (2) why it was sent back, (3) sandbox rules, (4) the implement skill.

Location: `src/orchestrator/agent.py`

### Step 4: Write tests for iteration limit enforcement

Write tests verifying:
1. Work unit with `implement_iterations >= max_iterations` is escalated to NEEDS_ATTENTION instead of dispatched
2. `implement_iterations` increments on every IMPLEMENT dispatch
3. The attention_reason includes the iteration count and explains the limit was hit
4. Non-IMPLEMENT phases are not affected by the iteration counter

Location: `tests/test_orchestrator_scheduler.py` or new test file

### Step 5: Increment `implement_iterations` and enforce limit in scheduler

In `scheduler.py`'s `_dispatch_work_unit()`, just before calling `run_phase()` for IMPLEMENT:

1. Load `max_iterations` from reviewer config (reuse the existing `load_reviewer_config()` call pattern)
2. Check `work_unit.implement_iterations >= max_iterations + 1` — if exceeded, escalate to NEEDS_ATTENTION with reason: `"Exceeded maximum implement iterations ({n}). The chunk may need operator guidance."`
3. Increment `work_unit.implement_iterations` and persist

The `+1` accounts for the initial implementation (iteration 0) — the limit applies to re-entries, so max_iterations=3 allows 1 initial + 3 re-entries = 4 total runs.

Location: `src/orchestrator/scheduler.py`

### Step 6: Pass `reentry_context` from scheduler to agent for each transition path

Thread the `reentry_context` string through the scheduler→agent call for each re-entry path:

**Path A — Unaddressed feedback reroute** (scheduler.py ~line 721):
When pre-review validation finds REVIEW_FEEDBACK.md still exists and reroutes to IMPLEMENT, store a reentry context on the work unit: `"Previous implementation did not address review feedback. The REVIEW_FEEDBACK.md file was not deleted, indicating feedback items remain unresolved. You MUST read and address every item in REVIEW_FEEDBACK.md, then delete the file."`

**Path B — Review FEEDBACK** (review_routing.py ~line 340-362):
Already handled by `orch_review_feedback_fidelity`. The REVIEW_FEEDBACK.md file IS the context. No additional reentry_context needed since `run_phase()` already detects and injects it.

**Path C — Operator answer after ESCALATE** (agent.py ~line 658-663):
Already handled via `pending_answer` injection. No change needed.

**Implementation approach**: Add a `reentry_context: Optional[str] = None` field to `WorkUnit`. The scheduler sets it at the point of transition, and `run_phase()` reads it from the work unit, injects it into the prompt, then clears it. This avoids threading the parameter through multiple call layers.

Location: `src/orchestrator/models.py`, `src/orchestrator/scheduler.py`, `src/orchestrator/agent.py`

### Step 7: Write integration test for full cycle

Write a test that simulates a multi-cycle scenario:
1. Work unit starts IMPLEMENT (iteration 0) → completes → REBASE → REVIEW → FEEDBACK
2. Re-enters IMPLEMENT (iteration 1) with feedback — prompt includes feedback content
3. Doesn't address feedback → pre-review reroutes to IMPLEMENT (iteration 2) — prompt includes "feedback not addressed" context
4. At iteration = max_iterations + 1, escalates to NEEDS_ATTENTION

This verifies the full interaction between iteration tracking, prompt injection, and limit enforcement.

Location: `tests/test_orchestrator_reentry.py` (new file)

### Step 8: Reset `implement_iterations` on successful REVIEW APPROVE

When a review APPROVE routes the work unit to COMPLETE, reset `implement_iterations = 0`. This is defensive — the counter shouldn't matter after APPROVE — but maintains clean state.

Location: `src/orchestrator/review_routing.py`

## Dependencies

- `orch_review_feedback_fidelity` (ACTIVE) — provides the REVIEW_FEEDBACK.md injection mechanism we extend

## Risks and Open Questions

- **Interaction with `review_iterations`**: Both counters increment on the review→feedback→implement path. `review_iterations` is used by the review routing to decide when to escalate from FEEDBACK. `implement_iterations` is used by the scheduler to enforce a global ceiling. They serve different purposes but overlap on the FEEDBACK path. The reviewer's `max_iterations` check in `_apply_review_decision` will fire first (it checks before creating the feedback file), so `implement_iterations` acts as a second safety net that also catches non-review re-entry paths.

- **`reentry_context` field persistence**: Adding a string field to WorkUnit means it gets serialized to SQLite. It will be `None` most of the time and only briefly set during transitions. This is acceptable — the field is small and the pattern matches `pending_answer`.

- **`max_iterations + 1` semantics**: The first IMPLEMENT run is the initial implementation, not a "re-entry." If `max_iterations=3`, we allow iterations 0 (initial), 1, 2, 3 (three re-entries) = 4 total. This matches the reviewer's semantics where `max_iterations=3` means 3 review cycles are allowed.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
