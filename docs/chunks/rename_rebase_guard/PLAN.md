<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The bug in `_detect_rename()` stems from incorrect assumptions about the
IMPLEMENTING set after certain orchestrator state transitions. The current logic
assumes the work unit's chunk will always be in the IMPLEMENTING set, but this
assumption fails in two scenarios:

1. **Post-COMPLETE rebase**: After COMPLETE phase runs, it changes the chunk's
   status from IMPLEMENTING to ACTIVE. If a merge conflict triggers
   `_handle_merge_conflict_retry()`, the work unit cycles back to REBASE phase.
   At this point, `_detect_rename()` scans for IMPLEMENTING chunks but finds the
   work unit's chunk is ACTIVE — it concludes "my chunk disappeared" even though
   it's still present.

2. **Rebase merging main**: When rebasing, main is merged into the worktree.
   Main only contains ACTIVE/FUTURE chunks (never IMPLEMENTING), yet the current
   implementation's set-difference logic can produce false positives when there
   are unexpected interactions between what's on main vs. the worktree.

**Fix strategy**: Reframe rename detection to focus on "is there a new
IMPLEMENTING chunk that wasn't in the baseline?" rather than "did my chunk
disappear from IMPLEMENTING?". The work unit's identity (`work_unit.chunk`)
should be the source of truth — we don't need to verify it's still IMPLEMENTING
because we *know* which chunk this work unit is managing.

**Key insight**: A rename can only happen during phases where the chunk is
IMPLEMENTING (specifically during PLAN when `suggest-prefix` runs). By the time
a work unit reaches COMPLETE or post-COMPLETE REBASE, renames are no longer
possible — the chunk's status has already been changed. Therefore, we should
skip rename detection entirely for post-PLAN phases where the chunk is no longer
expected to be IMPLEMENTING.

This approach builds on the existing `baseline_implementing` mechanism from
`orch_rename_propagation` but adds phase-aware guards.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a fix to
  the `_detect_rename()` method in the scheduler component. The orchestrator
  subsystem's invariant that "each phase is a fresh agent context" is relevant —
  rename detection must account for status transitions between phases.

## Sequence

### Step 1: Write failing tests for the two bug scenarios

Location: `tests/test_orch_rename_propagation.py`

Add tests to the `TestRenameDetection` class that reproduce the two failure
scenarios:

1. **Post-COMPLETE rebase test**: Create a work unit in REBASE phase where the
   chunk's status in the worktree is ACTIVE (simulating the post-COMPLETE state).
   The baseline_implementing contains the old IMPLEMENTING chunks. Verify that
   `_detect_rename()` returns `None` (no false positive rename detection).

2. **Rebase merging main test**: Create a work unit in REBASE phase. The baseline
   has `[chunk_a]`, the current IMPLEMENTING set has `[chunk_a]`, but there's
   also an ACTIVE chunk `chunk_b` that came from main. Verify that
   `_detect_rename()` returns `None` — only IMPLEMENTING chunks should be
   considered, so chunk_b (ACTIVE) should be ignored.

These tests should fail initially, demonstrating the bug.

### Step 2: Update `_detect_rename()` to use phase-aware detection

Location: `src/orchestrator/scheduler.py`

Modify `_detect_rename()` to:

1. **Check the work unit's phase**: If the phase is post-PLAN (IMPLEMENT,
   REBASE, REVIEW, COMPLETE), renames are no longer possible because:
   - Renames only happen via `suggest-prefix` during PLAN
   - By IMPLEMENT, the chunk directory has already been renamed (if at all)
   - After COMPLETE, the chunk status is ACTIVE, not IMPLEMENTING

   For these phases, return `None` early — no rename detection needed.

2. **For PLAN phase**: Keep the existing logic but with one key fix: instead of
   checking `work_unit.chunk in current_implementing`, check for
   `(current_implementing - baseline_set)`. A rename is detected only when:
   - `len(current_implementing - baseline_set) == 1` (exactly one new chunk)
   - The new chunk's name differs from `work_unit.chunk`

   This decouples rename detection from the work unit's chunk being IMPLEMENTING.

The updated logic should be:
```python
def _detect_rename(self, work_unit, worktree_path) -> tuple[str, str] | None:
    # Phase guard: renames only possible during PLAN
    if work_unit.phase != WorkUnitPhase.PLAN:
        return None

    # No baseline means we can't detect renames
    if not work_unit.baseline_implementing:
        return None

    # Get current IMPLEMENTING chunks
    current_implementing = set(chunks_manager.list_implementing_chunks())
    baseline_set = set(work_unit.baseline_implementing)

    # Check for new IMPLEMENTING chunks that weren't in baseline
    new_chunks = current_implementing - baseline_set

    if len(new_chunks) == 1:
        new_name = new_chunks.pop()
        # A rename occurred: new IMPLEMENTING chunk appeared
        return (work_unit.chunk, new_name)

    # No rename (or ambiguous)
    return None
```

### Step 3: Update the ambiguity handling in `_handle_agent_result()`

Location: `src/orchestrator/scheduler.py`

The current code at lines 848-869 handles ambiguous rename cases. Update this
logic to be phase-aware:

1. Move the ambiguity checks inside the `if rename_result is not None` block
2. Only check for "chunk disappeared" errors during PLAN phase
3. For post-PLAN phases, the work unit's chunk being absent from IMPLEMENTING
   is expected (it's now ACTIVE) — don't treat it as an error

The current code:
```python
elif work_unit.baseline_implementing and chunk not in work_unit.baseline_implementing:
    # Chunk disappeared but no clear rename detected
```

Should be guarded by phase check:
```python
elif work_unit.phase == WorkUnitPhase.PLAN and work_unit.baseline_implementing:
    # Only check for disappeared chunks during PLAN phase
    if chunk not in work_unit.baseline_implementing:
        # Check ambiguous cases...
```

### Step 4: Verify existing tests still pass

Run the existing rename propagation tests to ensure the fix doesn't break
normal rename detection during PLAN phase:

```bash
uv run pytest tests/test_orch_rename_propagation.py -v
```

All existing tests should pass, plus the two new tests from Step 1.

### Step 5: Add integration-level test scenarios

Location: `tests/test_orch_rename_propagation.py`

Add tests that verify the end-to-end behavior:

1. **Test: Rebase after COMPLETE does not false-positive**
   - Create work unit, simulate progression through PLAN → IMPLEMENT → REBASE →
     REVIEW → COMPLETE
   - Trigger merge conflict retry (back to REBASE)
   - Call `_detect_rename()` — should return `None`

2. **Test: Rebase merging ACTIVE chunks from main**
   - Create work unit with baseline_implementing = ["my_chunk"]
   - Simulate merging main which adds ACTIVE chunks to docs/chunks/
   - Call `_detect_rename()` — should return `None` (ACTIVE chunks ignored)

### Step 6: Update the backreference comment

Add a chunk backreference comment above `_detect_rename()`:

```python
# Chunk: docs/chunks/rename_rebase_guard - Phase-aware rename detection guard
def _detect_rename(self, work_unit: WorkUnit, worktree_path: Path) -> ...:
```

## Dependencies

No external dependencies. This chunk builds on the infrastructure from
`orch_rename_propagation` which introduced `_detect_rename()` and
`baseline_implementing`.

## Risks and Open Questions

1. **Edge case: GOAL phase renames?** The plan assumes renames only happen
   during PLAN phase. Could an operator rename a chunk during GOAL phase? The
   orchestrator currently starts at PLAN for injected chunks, but if GOAL phase
   is ever used, we'd need to include it in the "rename possible" phases.
   **Mitigation**: The phase guard can be `phase in (GOAL, PLAN)` to be safe.

2. **Baseline not captured for REBASE retries**: When `_handle_merge_conflict_retry()`
   cycles back to REBASE, the baseline_implementing snapshot was captured during
   the original PLAN activation. If the chunk directory was renamed since then,
   the baseline is stale. However, this is fine — by REBASE phase, renames are
   no longer possible, so the baseline isn't consulted anyway.

## Deviations

*To be populated during implementation.*