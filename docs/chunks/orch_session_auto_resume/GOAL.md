---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/retry.py
- src/orchestrator/scheduler.py
- tests/test_orchestrator_retry.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/retry.py#is_session_limit_error
    implements: "Session limit error detection with reset time pattern matching"
  - ref: src/orchestrator/retry.py#parse_reset_time
    implements: "Reset time parsing with timezone conversion to UTC"
  - ref: src/orchestrator/scheduler.py#Scheduler::_schedule_session_retry
    implements: "Schedule retry at parsed reset time instead of exponential backoff"
  - ref: src/orchestrator/scheduler.py#Scheduler::_handle_agent_result
    implements: "Priority-ordered error handling: session limit → 5xx → NEEDS_ATTENTION"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
depends_on: null
created_after:
- artifact_index_cache
- artifact_pattern_consolidation
- chunks_class_decouple
- scheduler_decompose_methods
---

# Auto-resume work units after session limit reset

## Minor Goal

When an agent hits a session/rate limit with a known reset time (e.g. "You've hit your limit - resets 10pm"), the orchestrator currently marks the work unit as NEEDS_ATTENTION, requiring manual operator intervention to set it back to READY. This is unnecessary toil — the error message contains enough information for the scheduler to automatically schedule a retry after the reset time.

This chunk teaches the scheduler to detect session-limit errors that include a reset time, parse the reset timestamp, and schedule an automatic retry instead of escalating to the operator. This extends the existing `orch_api_retry` infrastructure (which handles 5xx errors with exponential backoff) with a new category: session-limit errors with a deterministic resume time.

## Success Criteria

- Session-limit errors with a parseable reset time (e.g. "You've hit your limit - resets 10pm (America/New_York)") are detected by a new `is_session_limit_error` function in `retry.py`
- The reset time is parsed from the error string and converted to a UTC datetime
- The scheduler sets `next_retry_at` to the parsed reset time and transitions the work unit to READY (not NEEDS_ATTENTION)
- Session-limit errors WITHOUT a parseable reset time still escalate to NEEDS_ATTENTION as before
- The orchestrator log clearly indicates "Session limit hit, scheduled retry at {time}" rather than silently waiting
- Existing `orch_api_retry` tests continue to pass — this is additive, not a modification of 5xx retry behavior
- Tests cover: time parsing with timezone, time parsing without timezone, unparseable errors fall through to NEEDS_ATTENTION