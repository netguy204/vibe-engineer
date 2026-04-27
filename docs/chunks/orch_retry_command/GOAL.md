---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/api/attention.py
  - src/orchestrator/api/app.py
  - src/orchestrator/client.py
  - src/cli/orch.py
  - tests/test_orchestrator_retry_command.py
code_references:
  - ref: src/orchestrator/api/attention.py#retry_endpoint
    implements: "POST /work-units/{chunk}/retry - Properly resets work unit state for fresh retry"
  - ref: src/orchestrator/api/attention.py#retry_all_endpoint
    implements: "POST /work-units/retry-all - Batch retry with optional phase filtering"
  - ref: src/orchestrator/client.py#OrchestratorClient::retry_work_unit
    implements: "Client method for single work unit retry via HTTP"
  - ref: src/orchestrator/client.py#OrchestratorClient::retry_all_work_units
    implements: "Client method for batch retry with phase filter support"
  - ref: src/cli/orch.py#work_unit_retry
    implements: "ve orch work-unit retry <chunk> CLI command"
  - ref: src/cli/orch.py#orch_retry_all
    implements: "ve orch retry-all CLI command with --phase filter"
  - ref: tests/test_orchestrator_retry_command.py
    implements: "Test coverage for retry endpoints and state reset behavior"
narrative: null
investigation: orch_stuck_recovery
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_merge_rebase_retry
- orch_rename_propagation
---

# Chunk Goal

## Minor Goal

`ve orch work-unit retry <chunk>` transitions a NEEDS_ATTENTION work unit back to READY with correct state cleanup. It clears `session_id` (so the scheduler does not try to resume a dead Claude session), `attention_reason`, `api_retry_count`, and `next_retry_at`, and clears the `worktree` field if the path no longer exists on disk. The command refuses to retry work units not in NEEDS_ATTENTION status.

This behaves like the "answer" endpoint (`attention.py#answer_endpoint`) minus the answer payload — both properly clear stale state before transitioning to READY — and stands apart from the generic PATCH endpoint (`ve orch work-unit status <chunk> READY`), which only updates explicitly provided fields and leaves stale session/attention state intact.

`ve orch retry-all` performs the same reset across every NEEDS_ATTENTION work unit in one operation, with an optional `--phase` filter (e.g., `--phase REVIEW`) to scope the retry to chunks stuck at a specific phase. Both commands report how many work units were retried.

## Success Criteria

- `ve orch work-unit retry <chunk>` transitions NEEDS_ATTENTION → READY and clears: `session_id`, `attention_reason`, `api_retry_count`, `next_retry_at`
- If the worktree path in the work unit no longer exists on disk, the `worktree` field is cleared (so the scheduler creates a fresh one)
- The command refuses to retry work units not in NEEDS_ATTENTION status
- `ve orch retry-all` retries all NEEDS_ATTENTION work units in one operation
- `ve orch retry-all --phase REVIEW` only retries work units stuck at the REVIEW phase
- Both commands report how many work units were retried
- Corresponding API endpoints exist (`POST /work-units/{chunk}/retry` and `POST /work-units/retry-all`)
- Tests cover: single retry with state reset, retry-all, phase filtering, rejection of non-NEEDS_ATTENTION units