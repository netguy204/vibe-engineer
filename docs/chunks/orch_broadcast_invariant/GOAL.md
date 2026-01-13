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

Fix missing WebSocket broadcasts in the orchestrator scheduler and establish discoverable documentation that ensures future agents know when to emit dashboard updates.

### Problem

The orchestrator dashboard doesn't receive real-time updates for certain state transitions because the scheduler updates the database without broadcasting via WebSocket. This is a recurring pattern—each time we add scheduler logic that changes work unit state, we forget to broadcast.

### Specific Bugs

1. **RUNNING transition** (`src/orchestrator/scheduler.py:405-409`): When a work unit transitions from READY to RUNNING, the scheduler updates the database but doesn't broadcast. Dashboard shows "ready" indefinitely until refresh.

2. **READY transition on phase advance** (`src/orchestrator/scheduler.py:686-693`): When a work unit advances phases (e.g., PLAN → IMPLEMENT), the status changes to READY but no broadcast is sent.

3. **NEEDS_ATTENTION conflict transition** (investigation needed): When a conflict is detected and `_mark_needs_attention` is called (`src/orchestrator/scheduler.py:785-789`), the code *does* call the broadcast functions, but the dashboard doesn't receive the update. The broadcast code exists at lines 888-894, but something prevents delivery. Possible causes to investigate:
   - Race condition between WebSocket connection and scheduler loop
   - Exception being swallowed in the broadcast path
   - Timing issue where broadcast happens before dashboard reconnects after initial injection

### Root Cause

The API endpoints (`src/orchestrator/api.py`) consistently broadcast after state changes, but the scheduler (`src/orchestrator/scheduler.py`) does not. There's no documentation establishing this as an invariant, so agents adding scheduler logic don't know they need to broadcast.

### Solution

1. Fix the immediate bugs by adding `broadcast_work_unit_update()` calls
2. Create discoverable documentation (module docstring, subsystem doc, or inline comments) that establishes the invariant: **every work unit state change must broadcast via WebSocket**

The documentation must be placed where future agents will naturally encounter it when modifying scheduler code.

## Success Criteria

1. **RUNNING broadcast**: Dashboard receives real-time notification when work unit transitions to RUNNING

2. **Phase advance broadcast**: Dashboard receives real-time notification when work unit advances phases and becomes READY

3. **Invariant documented**: Clear documentation exists that:
   - States the invariant: "All work unit state changes must call `broadcast_work_unit_update()`"
   - Is discoverable by agents working on scheduler code (e.g., module docstring, prominent comment near state-change code, or subsystem doc)
   - Provides the pattern to follow (example code)

4. **All tests pass**: Existing orchestrator tests continue to pass