<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Modify `get_ready_queue()` in `src/orchestrator/state.py` to include critical-path awareness in its sort order. The implementation follows the same pattern already established in `get_attention_queue()` which computes a `blocks_count` for each work unit.

The core change:
1. Query READY work units
2. For each, compute `blocks_count` — the number of BLOCKED or READY work units that have this chunk in their `blocked_by` list
3. Sort by `blocks_count DESC, priority DESC, created_at ASC`
4. Apply limit if specified and return results

This mirrors the attention queue's approach but applies it to ready queue scheduling. The scheduler's `_dispatch_tick()` already consumes `get_ready_queue()` as-is, so no scheduler changes are needed.

**Performance consideration**: The GOAL states "typically <20 units" in the ready queue, and the per-unit COUNT query adds negligible overhead for this scale. If this becomes a bottleneck in the future, a single SQL query with subquery could compute all counts at once, but that optimization is premature for current usage.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS additional scheduling intelligence in the orchestrator's state layer. The change extends the existing queue query pattern without deviating from subsystem conventions.

## Sequence

### Step 1: Write failing test for critical-path ordering

Create a test in `tests/test_orchestrator_state.py` that verifies:
- A chunk blocking 2 others is returned before a chunk blocking 0
- Priority still acts as a tiebreaker when `blocks_count` is equal
- Created_at still acts as a tiebreaker when both `blocks_count` and `priority` are equal

Test cases:
1. Three READY chunks: chunk_a blocks 2, chunk_b blocks 0, chunk_c blocks 1
   - Expected order: chunk_a, chunk_c, chunk_b
2. Two READY chunks with same blocks_count but different priority
   - Higher priority should come first
3. Two READY chunks with same blocks_count and priority but different created_at
   - Earlier created_at should come first

Location: `tests/test_orchestrator_state.py`, new `TestReadyQueueCriticalPath` class

### Step 2: Modify get_ready_queue to compute blocks_count

Update `get_ready_queue()` in `src/orchestrator/state.py`:

1. Query READY work units (existing behavior)
2. For each READY unit, count work units that reference it in their `blocked_by` list, filtering to only BLOCKED or READY status (these are the units that would benefit from this chunk completing)
3. Sort results by `blocks_count DESC, priority DESC, created_at ASC`
4. Apply limit if specified

The blocks_count query should use the same JSON LIKE pattern as `get_attention_queue()`:
```sql
SELECT COUNT(*) FROM work_units
WHERE blocked_by LIKE ? AND status IN (?, ?)
```

Add a backreference comment:
```python
# Chunk: docs/chunks/orch_ready_critical_path - Critical-path scheduling for ready queue
```

Location: `src/orchestrator/state.py`, `get_ready_queue()` method

### Step 3: Verify tests pass and existing tests remain green

Run:
```bash
uv run pytest tests/test_orchestrator_state.py -v
```

All existing tests plus new critical-path tests should pass.

### Step 4: Update code_paths in GOAL.md

Add the touched files to the chunk's frontmatter:
- `src/orchestrator/state.py`
- `tests/test_orchestrator_state.py`

## Risks and Open Questions

- **Status filtering for blocks_count**: Should we count work units with any status in `blocked_by`, or only BLOCKED/READY status? The goal says "chunks that unblock the most other work" which suggests counting BLOCKED/READY work units that are actively waiting. DONE work units don't benefit from unblocking. This is the approach we'll take.

- **Limit interaction with sorting**: If a limit is applied before counting blocks, we might miss the most critical chunks. The implementation fetches all READY units, computes blocks_count, sorts, then applies limit. This ensures correct ordering even with limits.

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