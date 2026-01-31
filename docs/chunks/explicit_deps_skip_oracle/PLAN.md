# Implementation Plan

## Approach

Modify the scheduler's `_check_conflicts` method to check for `explicit_deps=True` at the start. When set, bypass all oracle-related logic and instead only check whether any chunk in the `blocked_by` list is currently RUNNING.

The implementation follows the "trust the declaration" principle: if an agent explicitly declares dependencies via the chunk's `depends_on` frontmatter (which sets `explicit_deps=True` and populates `blocked_by` at injection time), the scheduler trusts that declaration rather than using heuristic oracle detection.

This enables predictable parallel execution for well-structured batches where the intended execution order is known upfront, eliminating false positives from the oracle's semantic analysis.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS the oracle bypass logic within the scheduler component. The change follows existing patterns in `_check_conflicts` for verdict handling.

## Sequence

### Step 1: Add early exit for explicit_deps work units

At the start of `_check_conflicts`, check if `work_unit.explicit_deps` is True. If so:
1. Get the set of RUNNING chunk names
2. For each chunk in `work_unit.blocked_by`, check if it's in the RUNNING set
3. Return blockers without touching the oracle

Location: src/orchestrator/scheduler.py#Scheduler::_check_conflicts

### Step 2: Add tests for oracle bypass

Add a new test class `TestExplicitDepsOracleBypass` with tests covering:
1. Explicit-dep work units skip oracle calls (mock oracle, verify not called)
2. Explicit-dep work units block only when blocked_by chunks are RUNNING
3. Explicit-dep work units unblock when blocked_by chunks are DONE
4. Explicit-dep work units unblock when blocked_by chunks don't exist
5. Multiple blockers with partial RUNNING status
6. Non-explicit work units still use oracle analysis
7. Explicit-dep work units ignore other active chunks not in blocked_by

Location: tests/test_orchestrator_scheduler.py#TestExplicitDepsOracleBypass

### Step 3: Update GOAL.md code_paths

Add the touched files to code_paths for tracking.

## Dependencies

- `explicit_deps_workunit_flag` chunk (ACTIVE): Provides the `explicit_deps` field on WorkUnit model

## Risks and Open Questions

- None identified. The implementation is straightforward - the oracle import is already lazy (inside the function), so explicit-dep work units never trigger it.

## Deviations

None - implementation followed the plan exactly.
