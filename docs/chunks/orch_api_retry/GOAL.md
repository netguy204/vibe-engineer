---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/models.py
- src/orchestrator/state.py
- src/orchestrator/scheduler.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/models.py#OrchestratorConfig
    implements: "API retry configuration (initial delay, max delay, max attempts)"
  - ref: src/orchestrator/models.py#WorkUnit
    implements: "API retry state fields (api_retry_count, next_retry_at)"
  - ref: src/orchestrator/state.py#StateStore::_migrate_v12
    implements: "Database migration adding api_retry_count and next_retry_at columns"
  - ref: src/orchestrator/scheduler.py#is_retryable_api_error
    implements: "Pattern matching to detect 5xx API errors"
  - ref: src/orchestrator/scheduler.py#Scheduler::_schedule_api_retry
    implements: "Exponential backoff retry scheduling logic"
  - ref: src/orchestrator/scheduler.py#Scheduler::_dispatch_tick
    implements: "Dispatch loop respecting next_retry_at timing"
  - ref: src/orchestrator/scheduler.py#Scheduler::_handle_agent_result
    implements: "Error handling branching for retryable vs non-retryable errors"
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "Reset retry state on successful phase advancement"
  - ref: src/orchestrator/retry.py
    implements: "Pattern matching for retryable API errors"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_question_capture
---

# Chunk Goal

## Minor Goal

Add automatic retry with exponential backoff when orchestrator stages encounter Anthropic API 5xx errors. Currently, when a stage fails with an API error, it transitions to NEEDS_ATTENTION and requires manual intervention. Instead, the orchestrator should automatically inject a literal "continue" prompt into the session to resume the agent, using exponential backoff to avoid overwhelming the API during outages.

## Success Criteria

- When a stage encounters any API 5xx error (500, 502, 503, 529, etc.), the orchestrator automatically injects a literal "continue" prompt
- Exponential backoff starts at 100ms, doubles each retry, caps at 5s
- Maximum of 30 retry attempts before giving up
- The retry behavior is logged so operators can see what's happening
- After exhausting retries, the stage transitions to NEEDS_ATTENTION as it does today
- Non-5xx API errors (4xx, other failures) continue to transition to NEEDS_ATTENTION immediately