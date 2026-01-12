---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/models.py
- src/orchestrator/state.py
- src/orchestrator/scheduler.py
- src/ve.py
- tests/test_orchestrator_state.py
- tests/test_orchestrator_scheduler.py
- tests/test_orchestrator_cli.py
code_references:
  - ref: src/orchestrator/models.py#WorkUnit
    implements: "WorkUnit model with attention_reason field"
  - ref: src/orchestrator/models.py#WorkUnit::model_dump_json_serializable
    implements: "JSON serialization including attention_reason for API responses"
  - ref: src/orchestrator/state.py#StateStore::_migrate_v4
    implements: "Database migration adding attention_reason column"
  - ref: src/orchestrator/state.py#StateStore::_row_to_work_unit
    implements: "Reading attention_reason from database with fallback"
  - ref: src/orchestrator/state.py#StateStore::create_work_unit
    implements: "Persisting attention_reason on work unit creation"
  - ref: src/orchestrator/state.py#StateStore::update_work_unit
    implements: "Persisting attention_reason on work unit update"
  - ref: src/orchestrator/scheduler.py#Scheduler::_mark_needs_attention
    implements: "Setting attention_reason when marking work unit as NEEDS_ATTENTION"
  - ref: src/orchestrator/scheduler.py#Scheduler::_handle_agent_result
    implements: "Capturing question text as attention_reason for suspended agents"
  - ref: src/ve.py#orch_ps
    implements: "Displaying truncated attention_reason in ps output"
  - ref: src/ve.py#work_unit_show
    implements: "Displaying full attention_reason in work-unit show command"
  - ref: tests/test_orchestrator_state.py#TestAttentionReasonPersistence
    implements: "State persistence tests for attention_reason field"
  - ref: tests/test_orchestrator_scheduler.py#TestAttentionReason
    implements: "Scheduler tests for attention_reason tracking"
  - ref: tests/test_orchestrator_cli.py#TestWorkUnitShow
    implements: "CLI tests for work-unit show command"
  - ref: tests/test_orchestrator_cli.py#TestOrchPsAttentionReason
    implements: "CLI tests for ps command attention_reason display"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after:
- orch_scheduling
---

# Chunk Goal

## Minor Goal

Store and display the reason why a work unit needs attention, making it easy for operators to diagnose and resolve blocked work units without needing to dig through logs.

Currently when an agent fails or suspends (e.g., asking a question), the work unit status changes to NEEDS_ATTENTION but the operator has no way to know WHY without checking logs. This chunk adds structured reason tracking and display capabilities.

## Success Criteria

- WorkUnit model has an `attention_reason: Optional[str]` field to store the reason
- Scheduler populates `attention_reason` when setting status to NEEDS_ATTENTION (with error message or question text)
- `ve orch ps` shows a truncated reason in output for NEEDS_ATTENTION work units
- `ve orch work-unit show <chunk>` command displays full work unit details including the complete reason
- API endpoint `GET /work-units/{chunk}` returns the attention_reason in the response
- State store migration adds the attention_reason column
- Tests verify reason is captured for both error and suspension cases

