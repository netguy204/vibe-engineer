---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/state.py
  - tests/test_orchestrator_state.py
code_references:
  - ref: src/orchestrator/state.py#StateStore::get_ready_queue
    implements: "Critical-path scheduling logic with blocks_count DESC, priority DESC, created_at ASC ordering"
  - ref: tests/test_orchestrator_state.py#TestReadyQueueCriticalPath
    implements: "Test coverage for critical-path ordering: blocks_count priority, tiebreakers, status filtering"
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- cli_exit_codes
---

# Chunk Goal

## Minor Goal

The orchestrator's ready queue is critical-path aware: chunks that block other chunks are dispatched before independent leaf chunks.

`get_ready_queue()` in `src/orchestrator/state.py` orders READY work units by `blocks_count DESC, priority DESC, created_at ASC`. A chunk like `frontmatter_io` (which blocks `artifact_manager_base` and `validation_error_surface`) is dispatched ahead of independent chunks because its `blocks_count` is higher.

The attention queue (`get_attention_queue()`) computes the same `blocks_count` by counting how many other work units have it in their `blocked_by` list. The ready queue applies the same logic: chunks that unblock the most other work go first.

This advances the trunk goal's required property that the workflow "should not grow more difficult over time" — as dependency chains grow deeper, the scheduler automatically optimizes for throughput rather than requiring manual priority tuning.

## Success Criteria

- `get_ready_queue()` in `src/orchestrator/state.py` computes a `blocks_count` for each READY work unit (number of BLOCKED/READY work units that reference it in `blocked_by`)
- Sort order becomes: `blocks_count DESC, priority DESC, created_at ASC` — critical-path chunks are dispatched first, with existing priority and FIFO as tiebreakers
- When a batch like the `arch_consolidation` narrative is injected, `frontmatter_io` is dispatched before independent leaf chunks like `validation_length_msg`
- The `_dispatch_tick()` in `src/orchestrator/scheduler.py` requires no changes — it consumes the ready queue as-is
- Existing tests pass; new test verifies that a chunk blocking 2 others is returned before a chunk blocking 0
- Performance: the `blocks_count` query adds negligible overhead (single COUNT query per READY unit, typically <20 units)