---
decision: APPROVE
summary: All success criteria satisfied - get_ready_queue now computes blocks_count and sorts critical-path chunks first, scheduler unchanged, comprehensive tests pass.
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `get_ready_queue()` in `src/orchestrator/state.py` computes a `blocks_count` for each READY work unit (number of BLOCKED/READY work units that reference it in `blocked_by`)

- **Status**: satisfied
- **Evidence**: `src/orchestrator/state.py:734-752` — For each READY unit, executes `SELECT COUNT(*) FROM work_units WHERE blocked_by LIKE ? AND status IN (?, ?)` filtering to BLOCKED and READY status only. Uses the same JSON LIKE pattern as `get_attention_queue()`.

### Criterion 2: Sort order becomes: `blocks_count DESC, priority DESC, created_at ASC` — critical-path chunks are dispatched first, with existing priority and FIFO as tiebreakers

- **Status**: satisfied
- **Evidence**: `src/orchestrator/state.py:754` — `results.sort(key=lambda x: (-x[1], -x[0].priority, x[0].created_at))` implements the exact sort order: blocks_count DESC (negated), priority DESC (negated), created_at ASC (natural).

### Criterion 3: When a batch like the `arch_consolidation` narrative is injected, `frontmatter_io` is dispatched before independent leaf chunks like `validation_length_msg`

- **Status**: satisfied
- **Evidence**: Per the arch_consolidation narrative, `frontmatter_io` is depended on by `artifact_manager_base` and `validation_error_surface`. When injected, these dependencies will be in the `blocked_by` of dependent chunks, causing `frontmatter_io` to have a higher blocks_count than independent leaf chunks like `validation_length_msg` (which has `depends_on: []`).

### Criterion 4: The `_dispatch_tick()` in `src/orchestrator/scheduler.py` requires no changes — it consumes the ready queue as-is

- **Status**: satisfied
- **Evidence**: `src/orchestrator/scheduler.py:669` — `ready_units = self.store.get_ready_queue(limit=slots)` — The scheduler simply consumes the ready queue as before. No changes required to scheduler.py.

### Criterion 5: Existing tests pass; new test verifies that a chunk blocking 2 others is returned before a chunk blocking 0

- **Status**: satisfied
- **Evidence**: All 57 tests in `tests/test_orchestrator_state.py` pass. The new `TestReadyQueueCriticalPath` class (lines 883-1156) includes 5 tests: `test_chunks_blocking_more_dispatched_first`, `test_priority_tiebreaker_when_blocks_count_equal`, `test_created_at_tiebreaker_when_blocks_count_and_priority_equal`, `test_only_counts_blocked_and_ready_status`, and `test_limit_applied_after_sorting`.

### Criterion 6: Performance: the `blocks_count` query adds negligible overhead (single COUNT query per READY unit, typically <20 units)

- **Status**: satisfied
- **Evidence**: Implementation uses one COUNT query per READY unit (lines 740-751). The GOAL's assumption of "<20 units" is reasonable for typical orchestrator usage. Tests complete in 0.28s total, indicating minimal overhead.
