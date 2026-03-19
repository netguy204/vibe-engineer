---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/orch.py
- tests/test_orchestrator_retry_command.py
code_references:
- ref: src/cli/orch.py#orch_retry
  implements: "Top-level ve orch retry <chunk> CLI command for single work unit retry"
- ref: tests/test_orchestrator_retry_command.py#TestRetryCLI
  implements: "CLI tests for successful retry, not found, wrong state, JSON output, and path prefix stripping"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- board_watch_reconnect_delivery
---
# Chunk Goal

## Minor Goal

Add `ve orch retry <chunk_name>` to retry a single NEEDS_ATTENTION work unit by name.

Currently only `ve orch retry-all` exists, which retries every stuck unit. When debugging a single chunk, operators and stewards need to retry just that one without disturbing others that may be intentionally held in NEEDS_ATTENTION for investigation.

The command should:
- Accept a chunk name as argument
- Validate the chunk exists in the orchestrator and is in NEEDS_ATTENTION state
- Reset it to READY and requeue it for the next available phase
- Error clearly if the chunk doesn't exist or isn't in NEEDS_ATTENTION

## Success Criteria

- `ve orch retry <chunk_name>` resets a single NEEDS_ATTENTION work unit to READY
- Command errors with a clear message if the chunk doesn't exist in the orchestrator
- Command errors with a clear message if the chunk is not in NEEDS_ATTENTION state
- Existing `ve orch retry-all` behavior unchanged
- Tests cover: successful retry, chunk not found, chunk in wrong state

