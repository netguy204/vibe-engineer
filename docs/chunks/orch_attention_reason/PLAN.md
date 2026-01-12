<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds a simple `attention_reason` field to track why work units need
operator attention. The implementation extends existing orchestrator infrastructure:

1. **Model layer**: Add `attention_reason: Optional[str]` to the WorkUnit model
2. **Persistence layer**: Add database migration for the new column
3. **Scheduler layer**: Populate the field when transitioning to `NEEDS_ATTENTION`
4. **CLI layer**: Display the reason in `ve orch ps` (truncated) and `ve orch work-unit show` (full)
5. **API layer**: Return the field in `GET /work-units/{chunk}` responses

The approach follows existing patterns in the orchestrator codebase:
- SQLite migrations via `_migrate_vN()` methods in `state.py`
- Pydantic models with `model_dump_json_serializable()` for API responses
- Click CLI commands following existing `ve orch` patterns

Tests follow docs/trunk/TESTING_PHILOSOPHY.md:
- State persistence tests verify the field is stored, updated, and retrievable
- Scheduler tests verify the field is populated for error and suspension cases
- CLI tests verify the display format for both `ps` and `work-unit show` commands

## Sequence

### Step 1: Add attention_reason field to WorkUnit model

Add `attention_reason: Optional[str] = None` field to the WorkUnit model in
`src/orchestrator/models.py`. Include in `model_dump_json_serializable()` output.

Add chunk backreference comment above the WorkUnit class.

Location: src/orchestrator/models.py

### Step 2: Add database migration for attention_reason column

Create `_migrate_v4()` in `src/orchestrator/state.py` that adds the
`attention_reason TEXT` column to the `work_units` table. Increment
`CURRENT_VERSION` to 4.

Update `_row_to_work_unit()` to read the new column with fallback for older
databases. Update `create_work_unit()` and `update_work_unit()` to persist
the field.

Location: src/orchestrator/state.py

### Step 3: Populate attention_reason in scheduler

Modify `_mark_needs_attention()` in `src/orchestrator/scheduler.py` to accept
a `reason` parameter and store it in `work_unit.attention_reason`.

Update all callers of `_mark_needs_attention()`:
- Error results: pass the error message
- Suspension results: extract question text from `result.question`
- Verification failures: pass descriptive message

Update `_handle_agent_result()` for suspended results to capture the question
text as the attention reason (prefixed with "Question: ").

Location: src/orchestrator/scheduler.py

### Step 4: Display truncated reason in ve orch ps

Modify `orch_ps()` in `src/ve.py` to:
- Check if any `NEEDS_ATTENTION` work units have an `attention_reason`
- If so, add a REASON column to the table output
- Truncate reasons to 30 characters with "..." suffix

Location: src/ve.py

### Step 5: Add ve orch work-unit show command

Add a new `work_unit_show()` command in `src/ve.py` under the `work_unit` group.

The command:
- Takes a chunk name as argument
- Calls `client.get_work_unit(chunk)` to fetch details
- Displays all fields in a formatted output including the full `attention_reason`
- Supports `--json` flag for JSON output

Location: src/ve.py

### Step 6: Verify API returns attention_reason

The existing `GET /work-units/{chunk}` endpoint already returns the full WorkUnit
via `model_dump_json_serializable()`. Verify that `attention_reason` is included
in the response.

Location: src/orchestrator/api.py (verification only, no changes needed)

### Step 7: Add state persistence tests

Add `TestAttentionReasonPersistence` class in `tests/test_orchestrator_state.py`:
- `test_stores_attention_reason`: Create unit with reason, verify it persists
- `test_updates_attention_reason`: Update reason on existing unit
- `test_attention_reason_null_by_default`: Verify None when not set
- `test_clears_attention_reason`: Set reason then clear it
- `test_attention_reason_preserved_in_list`: Verify included in list results

Location: tests/test_orchestrator_state.py

### Step 8: Add scheduler attention_reason tests

Add `TestAttentionReason` class in `tests/test_orchestrator_scheduler.py`:
- `test_suspended_result_captures_question_as_reason`: Verify question text captured
- `test_suspended_result_without_question_uses_default`: Verify default message
- `test_error_result_stores_error_as_reason`: Verify error message captured
- `test_max_retries_stores_reason`: Verify retry exhaustion message
- `test_verification_error_stores_reason`: Verify verification error captured

Location: tests/test_orchestrator_scheduler.py

### Step 9: Add CLI tests for work-unit show

Add `TestWorkUnitShow` class in `tests/test_orchestrator_cli.py`:
- `test_show_work_unit_basic`: Verify basic output format
- `test_show_with_attention_reason`: Verify attention_reason displayed
- `test_show_json_output`: Verify JSON format
- `test_show_not_found`: Verify error handling

Location: tests/test_orchestrator_cli.py

### Step 10: Add CLI tests for ps with attention_reason

Add tests to existing `TestOrchPs` class in `tests/test_orchestrator_cli.py`:
- `test_ps_shows_attention_reason_column`: Verify REASON column appears
- `test_ps_truncates_long_reason`: Verify truncation to 30 chars

Location: tests/test_orchestrator_cli.py

## Dependencies

- **orch_scheduling** (complete): Provides the scheduler infrastructure where
  `_mark_needs_attention()` and `_handle_agent_result()` live

No external library dependencies.

## Risks and Open Questions

- **None identified**: This is a straightforward addition of a text field with
  no complex logic or external dependencies.

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

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->