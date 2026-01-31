---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/scheduler.py#Scheduler::_check_conflicts
    implements: "Oracle bypass logic for explicit-dep work units - skips oracle analysis when explicit_deps=True and only checks blocked_by against RUNNING chunks"
  - ref: tests/test_orchestrator_scheduler.py#TestExplicitDepsOracleBypass
    implements: "Test coverage for oracle bypass behavior including skipping oracle calls, blocking on RUNNING blockers, unblocking when done/nonexistent, multiple blockers, and non-explicit units still using oracle"
narrative: explicit_chunk_deps
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- explicit_deps_workunit_flag
created_after:
- orch_task_worktrees
---

# Chunk Goal

## Minor Goal

Modify the scheduler's `_check_conflicts` method to bypass the oracle entirely when a work unit has `explicit_deps=True`. For these work units, conflict detection relies solely on the `blocked_by` list that was set during injection, eliminating oracle false positives for well-structured batches.

Currently, all work units go through the oracle's `analyze_conflict` heuristic, which can produce false positives for semantically-related chunks that don't actually share file-level overlap. When agents explicitly declare dependencies during batch injection, they've already encoded the intended execution order - the oracle's heuristic detection is redundant and potentially counterproductive.

This chunk implements the "trust the declaration" path: if `explicit_deps=True`, the scheduler skips oracle analysis entirely. The only conflict check needed is whether any chunk in `blocked_by` is currently RUNNING - if so, block; if DONE or not running, allow dispatch. This makes explicit-dependency batches immune to oracle false positives.

## Success Criteria

1. **Oracle bypass for explicit-dep work units**: When `_check_conflicts` encounters a work unit with `explicit_deps=True`, it skips calling `oracle.analyze_conflict` entirely. No conflict verdicts are cached; the oracle is not involved.

2. **Blocked-by-only conflict detection**: For explicit-dep work units, the only blocking check is:
   - For each chunk in `work_unit.blocked_by`:
     - If that chunk's work unit is RUNNING → block (return chunk in blocking list)
     - If that chunk's work unit is DONE or doesn't exist → no block
   - No oracle heuristic analysis occurs

3. **Non-explicit work units unchanged**: Work units without `explicit_deps=True` continue using the existing oracle-based conflict detection logic unchanged.

4. **Unblock behavior unchanged**: The `_unblock_dependents` method already removes completed chunks from `blocked_by` lists. This chunk doesn't modify that behavior.

5. **Test coverage**:
   - Test that explicit-dep work units skip oracle calls (mock oracle, verify not called)
   - Test that explicit-dep work units block only when `blocked_by` chunks are RUNNING
   - Test that explicit-dep work units unblock when `blocked_by` chunks complete
   - Test that non-explicit work units still use oracle analysis

