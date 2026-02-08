<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk continues the decomposition work started by `scheduler_decompose` (which extracted `activation.py`, `review_parsing.py`, and `retry.py`). We now decompose the two remaining oversized methods:

1. **`_advance_phase`** (lines 562-753, ~192 lines): Extract completion/cleanup logic into `_finalize_completed_work_unit()`
2. **`_handle_review_result`** (lines 925-1135, ~210 lines): Extract into a standalone `review_routing.py` module

The decomposition follows the same patterns established by the prior chunk:
- Extract pure functions where possible to enable isolated testing
- Keep scheduler-specific state management in the Scheduler class
- New modules are thin wrappers around the extracted logic
- No behavioral changes — pure refactoring

Per `docs/trunk/TESTING_PHILOSOPHY.md`, existing tests must continue to pass without modification. New unit tests will be added for the extracted modules to enable isolated testing of the completion and routing logic.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS decomposition of the scheduler, which is core to the orchestrator subsystem. The extraction follows the existing patterns established by `scheduler_decompose`.

## Sequence

### Step 1: Extract `_finalize_completed_work_unit()` method

The `_advance_phase` method contains two distinct responsibilities:
1. **Phase progression** (lines 568-580, 731-753): Determining next phase and transitioning
2. **Completion/cleanup** (lines 583-729): ACTIVE verification, commits, restoration, finalization, DONE transition

Extract the completion block (when `next_phase is None`) into a new private method `_finalize_completed_work_unit()`. This method will:
- Verify chunk ACTIVE status via `verify_chunk_active_status()`
- Handle IMPLEMENTING status retries
- Commit uncommitted changes via `worktree_manager.commit_changes()`
- Restore displaced chunks via `restore_displaced_chunk()`
- Handle retained worktrees vs finalization
- Transition to DONE and unblock dependents

After extraction, `_advance_phase` will be ~80 lines:
- Phase progression map
- Early return call to `_finalize_completed_work_unit()` when `next_phase is None`
- Phase advancement logic (update phase, status, broadcast, reanalyze)

Location: `src/orchestrator/scheduler.py`

Backreference: Add `# Chunk: docs/chunks/scheduler_decompose_methods` to the new method

### Step 2: Create `review_routing.py` module

Create a new module at `src/orchestrator/review_routing.py` that extracts the review decision routing logic from `_handle_review_result`.

The module will contain:

```python
# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/scheduler_decompose_methods - Extracted from scheduler.py

async def route_review_decision(
    work_unit: WorkUnit,
    worktree_path: Path,
    result: AgentResult,
    config: ReviewRoutingConfig,
    callbacks: ReviewRoutingCallbacks,
) -> None:
    """Route work unit based on review decision.

    Handles:
    1. Review tool decision parsing (priority 1)
    2. Nudge logic when tool wasn't called
    3. File fallback parsing (priority 2)
    4. Log parsing fallback (priority 3)
    5. APPROVE/FEEDBACK/ESCALATE routing
    """
```

The module will define:
- `ReviewRoutingConfig`: dataclass with `max_iterations`, `max_nudges`, `log_dir_getter`
- `ReviewRoutingCallbacks`: protocol/dataclass with callbacks for:
  - `advance_phase(work_unit)` - for APPROVE routing
  - `mark_needs_attention(work_unit, reason)` - for ESCALATE routing
  - `update_work_unit(work_unit)` - for state persistence
  - `broadcast_work_unit_update(chunk, status, phase)` - for WebSocket updates
- Helper functions for the three-priority fallback chain

This keeps the review routing logic testable in isolation while allowing the scheduler to provide its concrete implementations.

Location: `src/orchestrator/review_routing.py`

### Step 3: Wire `review_routing.py` into scheduler

Update `scheduler.py` to import and use the new `review_routing` module:

1. Add import: `from orchestrator.review_routing import route_review_decision, ReviewRoutingConfig, ReviewRoutingCallbacks`
2. Replace `_handle_review_result` body with a thin wrapper that:
   - Creates `ReviewRoutingConfig` from `self.config` and `self.worktree_manager`
   - Creates `ReviewRoutingCallbacks` binding `self._advance_phase`, `self._mark_needs_attention`, etc.
   - Calls `route_review_decision()`

The `_handle_review_result` method will become ~20 lines of configuration and delegation.

Location: `src/orchestrator/scheduler.py`

### Step 4: Add tests for `review_routing.py`

Create `tests/test_orchestrator_review_routing.py` with isolated tests for:

1. **Decision routing tests**:
   - APPROVE decision calls `advance_phase` callback
   - FEEDBACK decision creates feedback file, returns to IMPLEMENT
   - ESCALATE decision calls `mark_needs_attention` callback

2. **Fallback chain tests**:
   - Priority 1: Tool decision used when present
   - Priority 2: File fallback when no tool decision
   - Priority 3: Log fallback when no file
   - Escalation when all fallbacks fail

3. **Nudge logic tests**:
   - Nudge increment when tool not called
   - Max nudges triggers fallback parsing
   - Nudge count reset on successful tool call

4. **Loop detection tests**:
   - Max iterations exceeded triggers escalation

Use mock callbacks to test routing logic in isolation without needing a full scheduler.

Location: `tests/test_orchestrator_review_routing.py`

### Step 5: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the files touched:
- `src/orchestrator/scheduler.py`
- `src/orchestrator/review_routing.py` (new)
- `tests/test_orchestrator_review_routing.py` (new)

### Step 6: Verify all tests pass

Run the full test suite to ensure no behavioral regressions:

```bash
uv run pytest tests/ -x -v
```

Specifically verify:
- All existing `test_orchestrator_scheduler.py` tests pass unchanged
- All existing `test_orchestrator_review_parsing.py` tests pass unchanged
- New `test_orchestrator_review_routing.py` tests pass
- Integration tests that exercise the full phase lifecycle pass

### Step 7: Measure line count reduction

Verify success criteria:
- `scheduler.py` is reduced by at least 200 lines (target: ~1063 lines or less)
- `_advance_phase` is under 80 lines
- `review_routing.py` is testable in isolation

```bash
wc -l src/orchestrator/scheduler.py
grep -n "async def _advance_phase" src/orchestrator/scheduler.py -A100 | head -100
```

## Dependencies

- Prior chunk `scheduler_decompose` must be complete (ACTIVE status) — already satisfied
- Existing `review_parsing.py` module — already exists

## Risks and Open Questions

1. **Callback pattern complexity**: The `ReviewRoutingCallbacks` pattern adds indirection. Alternative: extract pure functions that return routing decisions, let scheduler apply them. Decided to use callbacks for consistency with async nature of `_advance_phase` and `_mark_needs_attention`.

2. **`_finalize_completed_work_unit` naming**: Consider alternatives:
   - `_handle_completion()` — ambiguous
   - `_complete_work_unit()` — could be confused with COMPLETE phase
   - `_finalize_completed_work_unit()` — verbose but precise ✓

3. **WebSocket broadcast in extracted module**: The review routing needs to broadcast updates. Options:
   - Pass broadcast function as callback (chosen)
   - Import broadcast directly (creates tight coupling to websocket module)
   - Return events for scheduler to broadcast (more complex)

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
