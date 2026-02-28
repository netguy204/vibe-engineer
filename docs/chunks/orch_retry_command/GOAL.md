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

Add a `ve orch work-unit retry <chunk>` command that properly transitions a NEEDS_ATTENTION work unit back to READY with correct state cleanup. Currently, the only way to retry is the generic PATCH endpoint (`ve orch work-unit status <chunk> READY`), which does NOT clear stale state — leaving `session_id` pointing to a dead Claude session, stale `attention_reason`, and unreset retry counters. This causes the scheduler to attempt resuming a dead session on the next dispatch.

The "answer" endpoint (`attention.py:155`) is a good model — it properly clears `attention_reason`, sets `pending_answer`, and transitions to READY. The retry command should do the same minus the answer, plus reset `api_retry_count`, `next_retry_at`, and verify worktree validity.

Also add `ve orch retry-all` for batch retry of all NEEDS_ATTENTION work units, with optional `--phase` filter (e.g., `--phase REVIEW` to only retry chunks stuck at a specific phase).

## Success Criteria

- `ve orch work-unit retry <chunk>` transitions NEEDS_ATTENTION → READY and clears: `session_id`, `attention_reason`, `api_retry_count`, `next_retry_at`
- If the worktree path in the work unit no longer exists on disk, the `worktree` field is cleared (so the scheduler creates a fresh one)
- The command refuses to retry work units not in NEEDS_ATTENTION status
- `ve orch retry-all` retries all NEEDS_ATTENTION work units in one operation
- `ve orch retry-all --phase REVIEW` only retries work units stuck at the REVIEW phase
- Both commands report how many work units were retried
- Corresponding API endpoints exist (`POST /work-units/{chunk}/retry` and `POST /work-units/retry-all`)
- Tests cover: single retry with state reset, retry-all, phase filtering, rejection of non-NEEDS_ATTENTION units