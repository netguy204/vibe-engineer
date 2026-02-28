---
decision: APPROVE
summary: All success criteria satisfied - retry endpoints properly reset work unit state, CLI commands implemented, tests comprehensive with 16 passing tests
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve orch work-unit retry <chunk>` transitions NEEDS_ATTENTION → READY and clears: `session_id`, `attention_reason`, `api_retry_count`, `next_retry_at`

- **Status**: satisfied
- **Evidence**: `src/orchestrator/api/attention.py:222-226` explicitly sets `session_id = None`, `attention_reason = None`, `api_retry_count = 0`, `next_retry_at = None` before transitioning to `status = WorkUnitStatus.READY` at line 233. CLI command at `src/cli/orch.py:595-624` calls `client.retry_work_unit(chunk)`. Tests `test_retry_clears_session_id`, `test_retry_clears_attention_reason`, `test_retry_resets_api_retry_count`, `test_retry_clears_next_retry_at` all pass.

### Criterion 2: If the worktree path in the work unit no longer exists on disk, the `worktree` field is cleared (so the scheduler creates a fresh one)

- **Status**: satisfied
- **Evidence**: `src/orchestrator/api/attention.py:228-230` checks `if unit.worktree is not None and not Path(unit.worktree).exists(): unit.worktree = None`. Tests `test_retry_clears_invalid_worktree` and `test_retry_preserves_valid_worktree` verify this behavior correctly.

### Criterion 3: The command refuses to retry work units not in NEEDS_ATTENTION status

- **Status**: satisfied
- **Evidence**: `src/orchestrator/api/attention.py:215-220` validates status and returns 400 error with message "Only NEEDS_ATTENTION work units can be retried" if not in NEEDS_ATTENTION. Test `test_retry_rejects_non_needs_attention` verifies rejection for READY, RUNNING, BLOCKED, DONE statuses.

### Criterion 4: `ve orch retry-all` retries all NEEDS_ATTENTION work units in one operation

- **Status**: satisfied
- **Evidence**: `src/orchestrator/api/attention.py:260-334` implements `retry_all_endpoint` that lists all NEEDS_ATTENTION work units and applies the same state reset to each. CLI command at `src/cli/orch.py:627-660`. Test `test_retry_all_retries_all_needs_attention` verifies all 3 NEEDS_ATTENTION units are retried.

### Criterion 5: `ve orch retry-all --phase REVIEW` only retries work units stuck at the REVIEW phase

- **Status**: satisfied
- **Evidence**: `src/orchestrator/api/attention.py:271-283` parses optional `phase` query parameter, validates it's a valid `WorkUnitPhase`, and filters work units at lines 289-292. CLI passes `--phase` via `client.retry_all_work_units(phase=phase)`. Test `test_retry_all_with_phase_filter` creates 3 units at REVIEW, IMPLEMENT, PLAN phases and verifies only REVIEW is retried.

### Criterion 6: Both commands report how many work units were retried

- **Status**: satisfied
- **Evidence**: Single retry returns the updated work unit (CLI reports "Retried {chunk}, work unit queued for fresh dispatch"). Retry-all returns `{"count": N, "chunks": [...]}` at `attention.py:331-334`. CLI at `orch.py:648-659` reports "Retried {count} work unit(s)" with list. Test `test_retry_all_returns_count_and_chunks` verifies response format.

### Criterion 7: Corresponding API endpoints exist (`POST /work-units/{chunk}/retry` and `POST /work-units/retry-all`)

- **Status**: satisfied
- **Evidence**: Routes registered in `src/orchestrator/api/app.py:110` for retry-all and `app.py:119-124` for single retry. Endpoints imported from `attention.py` at `app.py:18-21`. All tests use direct HTTP calls via TestClient confirming routes work.

### Criterion 8: Tests cover: single retry with state reset, retry-all, phase filtering, rejection of non-NEEDS_ATTENTION units

- **Status**: satisfied
- **Evidence**: `tests/test_orchestrator_retry_command.py` contains 16 tests covering: state transitions (`test_retry_transitions_to_ready`), session_id clearing, attention_reason clearing, api_retry_count reset, next_retry_at clearing, worktree validity (invalid/valid), status rejection, 404 handling, retry-all batch operation, phase filtering, other status skipping, count/chunks response, empty response, invalid phase error, and batch state clearing. All 16 tests pass.

## Subsystem Invariant Check

The implementation respects orchestrator subsystem invariants:
- Thin CLI wrappers calling HTTP endpoints (per PROMPT.md convention)
- WebSocket broadcasts for state changes (`broadcast_attention_update`, `broadcast_work_unit_update`)
- Optimistic locking via `expected_updated_at` pattern
- Routes ordered correctly (specific before generic `{chunk:path}`)
- Proper backreference comments on all new code

## Additional Observations

- Code follows the `answer_endpoint` pattern from the investigation findings
- The decision to keep worktree validity check simple (just `Path.exists()`) matches the PLAN.md risk analysis
- Concurrent retry is handled gracefully by optimistic locking (StaleWriteError → skip in batch, 409 in single)
