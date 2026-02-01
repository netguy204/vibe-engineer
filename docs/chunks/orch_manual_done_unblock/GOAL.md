---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- src/orchestrator/api.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/scheduler.py#unblock_dependents
    implements: "Module-level function that unblocks dependent work units when a chunk completes"
  - ref: src/orchestrator/scheduler.py#Scheduler::_unblock_dependents
    implements: "Wrapper method for backward compatibility within Scheduler"
  - ref: src/orchestrator/api.py#update_work_unit_endpoint
    implements: "API endpoint that calls unblock_dependents when status is manually set to DONE"
  - ref: src/orchestrator/api.py#retry_merge_endpoint
    implements: "API endpoint that calls unblock_dependents after successful merge retry"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- reviewer_init_templates
- integrity_validate
- orch_reviewer_decision_mcp
---

# Chunk Goal

## Minor Goal

When an operator manually sets a work unit status to DONE (e.g., after resolving a merge conflict via `/orchestrator-investigate`), the scheduler should automatically re-evaluate and unblock any dependent work units. Currently, auto-unblock only triggers when the scheduler itself completes a work unit through normal flow, leaving dependent chunks stuck in BLOCKED status after manual intervention.

## Success Criteria

- When a work unit transitions to DONE (via API or CLI), the scheduler re-evaluates all BLOCKED work units
- Work units whose `blocked_by` dependencies are all DONE automatically transition to READY
- The unblock logic is triggered regardless of whether the DONE transition came from the scheduler or external source
- Tests verify that manual `ve orch work-unit status X DONE` unblocks dependent work units
- Existing auto-unblock behavior (from scheduler-completed work units) continues to work