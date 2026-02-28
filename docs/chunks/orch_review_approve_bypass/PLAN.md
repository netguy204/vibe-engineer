<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The bug is in `route_review_decision()` in `src/orchestrator/review_routing.py` (lines 191-203). The max iterations check fires **unconditionally** at the top of the function, before the review decision is even parsed. This means:

1. When `review_iterations + 1 > max_iterations`, the function immediately escalates to NEEDS_ATTENTION
2. The function returns early without checking what decision the reviewer actually made
3. Even if the reviewer returns APPROVE, the chunk escalates instead of completing

**Fix strategy**: Move the iteration limit check so it only applies when the review decision is FEEDBACK. The key insight is:
- **APPROVE** should always advance to COMPLETE, regardless of iteration count. If the reviewer approved after 5 iterations, the work is done.
- **FEEDBACK** is the only decision that should respect max_iterations, because FEEDBACK would trigger another review round.
- **ESCALATE** already routes to NEEDS_ATTENTION, so the iteration check is redundant there.

The fix will relocate the max_iterations guard into `_apply_review_decision()`, specifically within the FEEDBACK branch, right before setting up the next implement cycle.

Following the test-driven approach from TESTING_PHILOSOPHY.md, we write failing tests first that demonstrate the bug, then fix the implementation.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a bugfix within the orchestrator subsystem's review routing module. The subsystem is DOCUMENTED status, so no opportunistic improvements beyond the bug fix.

## Sequence

### Step 1: Write failing tests that demonstrate the bug

Add tests to `tests/test_orchestrator_review_routing.py` that exercise the bug:

1. **`test_approve_after_max_iterations_still_completes`**: Create a work unit at `review_iterations=3` (at max), return APPROVE via tool decision, and assert that `advance_phase` is called (not `mark_needs_attention`).

2. **`test_feedback_after_max_iterations_escalates`**: Create a work unit at `review_iterations=3`, return FEEDBACK, and assert that `mark_needs_attention` is called with the iteration limit message. This tests the *correct* behavior we want to preserve.

These tests should fail with the current implementation (Step 1 will incorrectly escalate).

Location: `tests/test_orchestrator_review_routing.py`

### Step 2: Remove the unconditional max iterations check from route_review_decision

In `src/orchestrator/review_routing.py`, remove the early return that fires before decision parsing (lines 191-203):

```python
# REMOVE THIS BLOCK:
current_iteration = work_unit.review_iterations + 1
if current_iteration > config.max_iterations:
    logger.warning(...)
    await callbacks.mark_needs_attention(...)
    return
```

Keep the `current_iteration` calculation for use later in the function.

Location: `src/orchestrator/review_routing.py#route_review_decision`

### Step 3: Add iteration limit check to the FEEDBACK branch in _apply_review_decision

In `_apply_review_decision()`, add the max iterations check **inside** the FEEDBACK branch, after logging but before creating the feedback file. The function needs access to the config, so update its signature to accept `ReviewRoutingConfig`.

```python
async def _apply_review_decision(
    work_unit: WorkUnit,
    worktree_path: Path,
    review_result: ReviewResult,
    current_iteration: int,
    session_id: Optional[str],
    callbacks: ReviewRoutingCallbacks,
    config: ReviewRoutingConfig,  # NEW PARAMETER
) -> None:
```

Inside the FEEDBACK branch:
```python
elif review_result.decision == ReviewDecision.FEEDBACK:
    # Check iteration limit BEFORE cycling back to implement
    if current_iteration >= config.max_iterations:
        logger.warning(
            f"Chunk {chunk} exceeded max review iterations ({config.max_iterations}) "
            f"with FEEDBACK - escalating"
        )
        await callbacks.mark_needs_attention(
            work_unit,
            f"Auto-escalated: exceeded maximum review iterations ({config.max_iterations}). "
            f"The implementation may need significant rework or the requirements "
            f"may be unclear. Last feedback: {review_result.summary}",
        )
        return

    # ... existing FEEDBACK logic continues ...
```

Note: The check uses `>=` because `current_iteration` is already incremented (it represents "this is iteration N"), so at iteration 3 of 3, we've hit the max.

Location: `src/orchestrator/review_routing.py#_apply_review_decision`

### Step 4: Update the call site to pass config

Update the call to `_apply_review_decision` in `route_review_decision` to include the config parameter:

```python
await _apply_review_decision(
    work_unit,
    worktree_path,
    review_result,
    current_iteration,
    result.session_id,
    callbacks,
    config,  # ADD THIS
)
```

Location: `src/orchestrator/review_routing.py#route_review_decision`

### Step 5: Update existing test to reflect new behavior

The existing test `test_max_iterations_triggers_escalation` needs adjustment. It currently:
- Creates a work unit with `review_iterations=3`
- Passes an AgentResult with no decision
- Expects escalation due to max iterations

But with our fix, the max iterations check only fires on FEEDBACK. Update the test to:
- Return a FEEDBACK decision via the tool
- Verify escalation happens with the FEEDBACK-specific message

Location: `tests/test_orchestrator_review_routing.py#test_max_iterations_triggers_escalation`

### Step 6: Run tests and verify

Run the test suite to verify:
1. New tests pass (approve-after-max-iterations works)
2. Updated test passes (feedback-at-max-iterations escalates)
3. All existing tests still pass (no regression)

```bash
uv run pytest tests/test_orchestrator_review_routing.py -v
```

## Dependencies

None. This is a self-contained bug fix within the existing review routing module.

## Risks and Open Questions

1. **Nudge flow interaction**: When nudging (tool not called), the function currently returns early before checking max iterations. With the fix, if an agent repeatedly doesn't call the tool, nudges will continue until `max_nudges`, then fall back to file/log parsing, then either succeed or escalate due to "no decision found" — not due to max iterations. This is arguably correct behavior (iteration limit is about review feedback loops, not nudge attempts), but worth verifying the test coverage.

2. **Iteration semantics on edge case**: The check `current_iteration >= config.max_iterations` assumes `current_iteration` is the iteration we're *completing*. If `max_iterations=3` and we're on iteration 3 returning FEEDBACK, we escalate because we can't start iteration 4. Need to verify this matches the documented behavior and existing test expectations.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->