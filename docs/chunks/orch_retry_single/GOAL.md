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

`ve orch retry <chunk_name>` retries a single NEEDS_ATTENTION work unit by name, alongside the batch `ve orch retry-all` form.

The single-chunk variant exists so operators and stewards can retry one chunk without disturbing other units that may be intentionally held in NEEDS_ATTENTION for investigation.

The command:
- Accepts a chunk name as argument
- Validates the chunk exists in the orchestrator and is in NEEDS_ATTENTION state
- Resets it to READY and requeues it for the next available phase
- Errors clearly if the chunk doesn't exist or isn't in NEEDS_ATTENTION

## Success Criteria

- `ve orch retry <chunk_name>` resets a single NEEDS_ATTENTION work unit to READY
- Command errors with a clear message if the chunk doesn't exist in the orchestrator
- Command errors with a clear message if the chunk is not in NEEDS_ATTENTION state
- Existing `ve orch retry-all` behavior unchanged
- Tests cover: successful retry, chunk not found, chunk in wrong state

