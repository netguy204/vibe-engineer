---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/scheduler.py#Scheduler
    implements: "WebSocket broadcasting invariant documentation in class docstring"
  - ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
    implements: "Broadcast RUNNING status when work unit is dispatched"
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "Broadcast READY status on phase advancement and DONE status on completion"
  - ref: tests/test_orchestrator_scheduler.py#TestWebSocketBroadcasts
    implements: "Test coverage for WebSocket broadcast invariant"
narrative: null
investigation: null
subsystems: []
friction_entries: []
created_after:
- cluster_list_command
- cluster_naming_guidance
- friction_chunk_workflow
- narrative_consolidation
---

# Chunk Goal

## Minor Goal

Establish a WebSocket broadcast invariant for the orchestrator scheduler: every work unit state change must call `broadcast_work_unit_update()` so the dashboard receives real-time updates, with discoverable documentation so future agents follow the invariant when adding scheduler logic.

### Invariant

Every transition of a work unit's status (RUNNING, READY on phase advance, DONE, NEEDS_ATTENTION, etc.) is paired with a `broadcast_work_unit_update()` call. The scheduler must broadcast for the same reason API endpoints in `src/orchestrator/api.py` already do: dashboards reading from the database alone cannot observe transitions in real time.

### Specific Transitions Covered

1. **RUNNING transition** (`src/orchestrator/scheduler.py` `_run_work_unit`): When a work unit transitions from READY to RUNNING, the scheduler broadcasts so the dashboard reflects the dispatch immediately.

2. **READY / DONE transitions on phase advance** (`src/orchestrator/scheduler.py` `_advance_phase`): When a work unit advances phases (e.g., PLAN → IMPLEMENT) the status returns to READY, and on completion it transitions to DONE; both transitions broadcast.

3. **NEEDS_ATTENTION conflict transition**: When `_mark_needs_attention` runs on a detected conflict, the broadcast is issued. (Earlier suspected delivery issues at this site—race conditions with WebSocket connect, swallowed exceptions, or timing relative to dashboard reconnect—remain open for separate investigation; the invariant only requires the broadcast call, not delivery guarantees, which are owned by the WebSocket layer.)

### Discoverability

The invariant is documented at the `Scheduler` class docstring in `src/orchestrator/scheduler.py` so any agent modifying scheduler code encounters the rule alongside the code that must obey it. Module-level imports and inline comments at each broadcast call site reinforce the pattern.

## Success Criteria

1. **RUNNING broadcast**: Dashboard receives real-time notification when work unit transitions to RUNNING

2. **Phase advance broadcast**: Dashboard receives real-time notification when work unit advances phases and becomes READY

3. **Invariant documented**: Clear documentation exists that:
   - States the invariant: "All work unit state changes must call `broadcast_work_unit_update()`"
   - Is discoverable by agents working on scheduler code (e.g., module docstring, prominent comment near state-change code, or subsystem doc)
   - Provides the pattern to follow (example code)

4. **All tests pass**: Existing orchestrator tests continue to pass