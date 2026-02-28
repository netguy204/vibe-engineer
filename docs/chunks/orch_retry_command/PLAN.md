<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add dedicated retry commands that properly reset work unit state, unlike the generic PATCH endpoint which only updates explicitly provided fields. The "answer" endpoint (`attention.py:106-186`) provides the model for proper state reset: it clears `attention_reason`, sets `pending_answer`, and transitions to READY with timestamp update.

The retry command extends this pattern to:
1. Clear `session_id` (prevents dead session resume)
2. Clear `attention_reason` (the issue is being retried, not answered)
3. Reset `api_retry_count` to 0 (fresh retry budget)
4. Clear `next_retry_at` (immediate scheduling)
5. Verify worktree validity (clear if path doesn't exist)
6. Transition NEEDS_ATTENTION → READY

Implementation follows existing patterns from DEC-007 (daemon HTTP API), DEC-008 (Pydantic models), and the orchestrator subsystem conventions.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS the retry command as a new endpoint and CLI command. The orchestrator subsystem documents the API structure (work_units.py for CRUD, attention.py for attention queue) which this chunk extends.

## Sequence

### Step 1: Add retry endpoint to attention.py

Create `retry_endpoint` function in `src/orchestrator/api/attention.py` that:

1. Accepts `POST /work-units/{chunk}/retry`
2. Validates work unit exists and is in NEEDS_ATTENTION status
3. Clears stale state: `session_id = None`, `attention_reason = None`, `api_retry_count = 0`, `next_retry_at = None`
4. Checks if `worktree` path exists on disk; if not, sets `worktree = None`
5. Transitions `status` to READY
6. Uses optimistic locking (per `optimistic_locking` chunk pattern)
7. Broadcasts updates via WebSocket
8. Returns the updated work unit

Location: `src/orchestrator/api/attention.py`

### Step 2: Add retry-all endpoint to attention.py

Create `retry_all_endpoint` function in `src/orchestrator/api/attention.py` that:

1. Accepts `POST /work-units/retry-all`
2. Accepts optional `phase` query parameter (e.g., `?phase=REVIEW`)
3. Lists all NEEDS_ATTENTION work units (filtered by phase if provided)
4. Calls the same state-reset logic from Step 1 for each
5. Returns count of retried work units and list of chunk names

Location: `src/orchestrator/api/attention.py`

### Step 3: Register routes in app.py

Add routes for the new endpoints to `src/orchestrator/api/app.py`:

```python
Route("/work-units/{chunk}/retry", endpoint=retry_endpoint, methods=["POST"]),
Route("/work-units/retry-all", endpoint=retry_all_endpoint, methods=["POST"]),
```

The retry-all route must come before the generic `{chunk:path}` routes.

Location: `src/orchestrator/api/app.py`

### Step 4: Add client methods

Add `retry_work_unit` and `retry_all_work_units` methods to `OrchestratorClient` class:

```python
def retry_work_unit(self, chunk: str) -> dict:
    """Retry a NEEDS_ATTENTION work unit with proper state reset."""
    return self._request("POST", f"/work-units/{chunk}/retry")

def retry_all_work_units(self, phase: Optional[str] = None) -> dict:
    """Retry all NEEDS_ATTENTION work units."""
    params = {"phase": phase} if phase else None
    return self._request("POST", "/work-units/retry-all", params=params)
```

Location: `src/orchestrator/client.py`

### Step 5: Add CLI commands

Add `ve orch work-unit retry <chunk>` command to the `work_unit` group:

```python
@work_unit.command("retry")
@click.argument("chunk")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_retry(chunk, json_output, project_dir):
    """Retry a NEEDS_ATTENTION work unit with proper state reset."""
```

Add `ve orch retry-all` command to the `orch` group:

```python
@orch.command("retry-all")
@click.option("--phase", type=str, help="Only retry chunks at this phase (e.g., REVIEW)")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_retry_all(phase, json_output, project_dir):
    """Retry all NEEDS_ATTENTION work units with proper state reset."""
```

Location: `src/cli/orch.py`

### Step 6: Write tests for retry endpoint

Create tests in a new test file `tests/test_orchestrator_retry_command.py`:

1. **test_retry_transitions_to_ready**: Create NEEDS_ATTENTION work unit, call retry, verify status is READY
2. **test_retry_clears_session_id**: Create work unit with session_id set, verify cleared after retry
3. **test_retry_clears_attention_reason**: Create work unit with attention_reason, verify cleared
4. **test_retry_resets_api_retry_count**: Create work unit with api_retry_count > 0, verify reset to 0
5. **test_retry_clears_next_retry_at**: Create work unit with next_retry_at set, verify cleared
6. **test_retry_clears_invalid_worktree**: Create work unit with worktree path that doesn't exist, verify cleared
7. **test_retry_preserves_valid_worktree**: Create work unit with valid worktree path, verify preserved
8. **test_retry_rejects_non_needs_attention**: Attempt to retry READY/RUNNING/DONE work unit, verify 400 error
9. **test_retry_not_found**: Attempt to retry non-existent chunk, verify 404

Location: `tests/test_orchestrator_retry_command.py`

### Step 7: Write tests for retry-all endpoint

Add tests to `tests/test_orchestrator_retry_command.py`:

1. **test_retry_all_retries_all_needs_attention**: Create multiple NEEDS_ATTENTION work units, verify all retried
2. **test_retry_all_with_phase_filter**: Create NEEDS_ATTENTION at different phases, verify only matching phase retried
3. **test_retry_all_skips_other_statuses**: Create mix of statuses, verify only NEEDS_ATTENTION affected
4. **test_retry_all_returns_count_and_chunks**: Verify response includes count and chunk names
5. **test_retry_all_empty_returns_zero**: No NEEDS_ATTENTION work units, verify count is 0

Location: `tests/test_orchestrator_retry_command.py`

### Step 8: Add backreference comments

Add appropriate chunk backreference comments to all new code:

```python
# Chunk: docs/chunks/orch_retry_command - Retry endpoint for NEEDS_ATTENTION work units
```

## Dependencies

- None. This chunk builds on existing orchestrator infrastructure without requiring other chunks to complete first.

## Risks and Open Questions

1. **Worktree validity check**: Checking if a worktree path exists is simple (`Path(worktree).exists()`), but should we also verify it's a valid git worktree? Decision: Keep it simple - just check existence. A non-existent path is definitely invalid; a corrupt worktree is a separate problem.

2. **Concurrent retry attempts**: What if two operators retry the same chunk simultaneously? The optimistic locking pattern (already used in answer_endpoint) handles this by detecting stale writes.

3. **Batch retry atomicity**: If retry-all fails midway, should we roll back successful retries? Decision: No - it's better to have partial progress than all-or-nothing. Each retry is independent.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.
-->
