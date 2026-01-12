<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk builds the attention queue system - the operator-facing interface for managing work units that need human input. Building on orch_attention_reason (which stores WHY work units need attention), this chunk adds the prioritization logic, display commands, and answer/resume workflow.

**Key technical choices:**

1. **Priority scoring in the database**: Store a computed `attention_priority` score based on downstream impact. This score combines:
   - Number of work units transitively blocked by this one
   - Time in NEEDS_ATTENTION state (older items surface first)

   This is simpler than the design doc's "depth_in_graph * weight" approach since we don't yet have complex dependency graphs.

2. **Answer injects response into resumed session**: When an operator answers a question:
   - The response text is stored temporarily on the work unit
   - Work unit transitions NEEDS_ATTENTION → READY (not directly to RUNNING)
   - Scheduler picks up the READY work unit and resumes the session
   - Resume includes the answer text injected as a user message

   This aligns with how orch_scheduling handles session suspension/resumption.

3. **Attention queue as a view, not separate storage**: Rather than duplicating data, the attention queue is computed from NEEDS_ATTENTION work units with priority scoring applied at query time.

**Patterns from existing orchestrator code:**
- Starlette HTTP endpoints (src/orchestrator/api.py)
- Click CLI commands with --json support (src/ve.py)
- OrchestratorClient for daemon communication (src/orchestrator/client.py)
- StateStore for database operations (src/orchestrator/state.py)

**Testing approach per docs/trunk/TESTING_PHILOSOPHY.md:**
- Test attention queue ordering with multiple NEEDS_ATTENTION work units
- Test answer command transitions and error cases
- Test resume with injected answer in agent runner
- Mock agent SDK for resume tests

## Subsystem Considerations

No existing subsystems are directly relevant to this chunk. The orchestrator is a new major component that may become a subsystem itself once stable.

## Sequence

### Step 1: Add answer storage field to WorkUnit model

Add `pending_answer: Optional[str] = None` field to the WorkUnit model in `src/orchestrator/models.py`. This field temporarily stores the operator's answer until the agent resumes and consumes it.

Update `model_dump_json_serializable()` to include the field.

Add chunk backreference comment.

Location: src/orchestrator/models.py

### Step 2: Add database migration for pending_answer column

Create `_migrate_v6()` in `src/orchestrator/state.py` that adds the `pending_answer TEXT` column to the `work_units` table. Increment `CURRENT_VERSION` to 6.

Update `_row_to_work_unit()` to read the new column with fallback for older databases. Update `create_work_unit()` and `update_work_unit()` to persist the field.

Location: src/orchestrator/state.py

### Step 3: Add get_attention_queue method to StateStore

Create `get_attention_queue()` method in `src/orchestrator/state.py` that:
1. Queries work units with status = NEEDS_ATTENTION
2. For each, computes the "blocks count" - how many other work units have this chunk in their blocked_by list
3. Orders by: blocks_count DESC, updated_at ASC (older items first among equal priority)
4. Returns list of WorkUnit objects with computed blocks_count metadata

The blocks_count is computed via a subquery or join, not stored persistently.

Location: src/orchestrator/state.py

### Step 4: Add GET /attention endpoint

Create `attention_endpoint()` in `src/orchestrator/api.py` that:
1. Calls `store.get_attention_queue()`
2. For each item, loads chunk goal summary from GOAL.md (first 200 chars of Minor Goal section)
3. Returns JSON with enriched attention items including:
   - chunk, phase, status, attention_reason
   - blocks_count (how many work units blocked)
   - time_waiting (seconds since status changed to NEEDS_ATTENTION)
   - goal_summary (truncated chunk goal for context)

Add route to create_app().

Location: src/orchestrator/api.py

### Step 5: Add POST /work-units/{chunk}/answer endpoint

Create `answer_endpoint()` in `src/orchestrator/api.py` that:
1. Validates work unit exists and is in NEEDS_ATTENTION state
2. Accepts JSON body with `answer: string`
3. Stores answer in `work_unit.pending_answer`
4. Clears `attention_reason` (it's been addressed)
5. Transitions status: NEEDS_ATTENTION → READY
6. Returns updated work unit

Add route to create_app().

Location: src/orchestrator/api.py

### Step 6: Modify scheduler to inject answer on resume

Update `_run_work_unit()` in `src/orchestrator/scheduler.py` to:
1. Check if `work_unit.pending_answer` is set
2. If set, pass the answer to `agent_runner.run_phase()` as a new parameter
3. After successful phase start, clear `pending_answer` from work unit

Location: src/orchestrator/scheduler.py

### Step 7: Update AgentRunner to accept and inject answer

Modify `run_phase()` in `src/orchestrator/agent.py` to:
1. Accept optional `pending_answer: Optional[str]` parameter
2. When resuming a session with a pending answer:
   - Include the answer in the initial prompt/message
   - Use format: "Operator response to your question: {answer}"
3. The answer becomes part of the conversation context for the resumed session

Location: src/orchestrator/agent.py

### Step 8: Add ve orch attention CLI command

Create `orch_attention()` command in `src/ve.py` that:
1. Calls `GET /attention` endpoint via client
2. Displays formatted attention queue:
   ```
   ATTENTION QUEUE (3 items)
   ─────────────────────────────────────────────────────────
   [1] auth_refactor  PLAN  blocks:4  waiting:12m
       Question: JWT or session tokens for auth layer?
       Goal: Refactor authentication to support SSO...

   [2] cache_layer  IMPLEMENT  blocks:1  waiting:5m
       Error: Test failure in test_cache_invalidation
       Goal: Add Redis-based caching for API responses...
   ```
3. Support `--json` flag for JSON output
4. Show "No work units need attention" if queue empty

Location: src/ve.py

### Step 9: Add ve orch answer CLI command

Create `orch_answer()` command in `src/ve.py` that:
1. Takes chunk name and answer text as arguments
2. Calls `POST /work-units/{chunk}/answer` endpoint
3. Displays confirmation: "Answered {chunk}, work unit queued for resume"
4. Support `--json` flag for JSON output
5. Handle errors: not found, not in NEEDS_ATTENTION state

Location: src/ve.py

### Step 10: Add client methods for attention queue

Add methods to `OrchestratorClient` in `src/orchestrator/client.py`:
1. `get_attention_queue()` - calls GET /attention
2. `answer_work_unit(chunk: str, answer: str)` - calls POST /work-units/{chunk}/answer

Location: src/orchestrator/client.py

### Step 11: Write tests for attention queue functionality

Create `tests/test_orchestrator_attention.py` with tests:

**StateStore tests:**
- `test_get_attention_queue_empty` - returns empty list when no NEEDS_ATTENTION
- `test_get_attention_queue_orders_by_blocks_count` - higher blocked count first
- `test_get_attention_queue_orders_by_time_when_equal_blocks` - older first among equals
- `test_get_attention_queue_excludes_non_needs_attention` - only NEEDS_ATTENTION status

**API tests:**
- `test_attention_endpoint_returns_enriched_items` - includes blocks_count, time_waiting
- `test_answer_endpoint_stores_answer_and_transitions` - NEEDS_ATTENTION → READY
- `test_answer_endpoint_rejects_wrong_status` - error if not NEEDS_ATTENTION
- `test_answer_endpoint_not_found` - 404 for unknown chunk

Location: tests/test_orchestrator_attention.py

### Step 12: Write tests for answer injection in scheduler

Add tests to `tests/test_orchestrator_scheduler.py`:
- `test_run_work_unit_with_pending_answer_passes_to_agent` - answer is passed
- `test_run_work_unit_clears_pending_answer_after_dispatch` - cleanup happens
- `test_pending_answer_included_in_resume_prompt` - verify agent receives it

Location: tests/test_orchestrator_scheduler.py

### Step 13: Write CLI tests for attention and answer commands

Add tests to `tests/test_orchestrator_cli.py`:

**TestOrchAttention class:**
- `test_attention_empty` - shows "No work units need attention"
- `test_attention_with_items` - shows formatted queue
- `test_attention_json` - JSON output format

**TestOrchAnswer class:**
- `test_answer_success` - transitions and confirms
- `test_answer_not_found` - shows error
- `test_answer_wrong_status` - shows error
- `test_answer_json` - JSON output format

Location: tests/test_orchestrator_cli.py

### Step 14: Integration test for full answer-resume flow

Add integration test to verify the complete flow:
1. Inject a chunk, agent runs until AskUserQuestion
2. Work unit becomes NEEDS_ATTENTION with question
3. Operator answers via `ve orch answer`
4. Work unit becomes READY with pending_answer
5. Scheduler resumes agent with answer injected
6. Agent proceeds with the answer in context

This may require mocking the agent SDK or using a controlled test fixture.

Location: tests/test_orchestrator_attention.py (or test_orchestrator_integration.py if appropriate)

## Dependencies

**Chunks:**
- `orch_attention_reason` (ACTIVE) - Provides `attention_reason` field on WorkUnit
- `orch_scheduling` (ACTIVE) - Provides scheduler, agent runner, session resumption

**No external library dependencies** beyond what's already installed.

## Risks and Open Questions

1. **Goal summary extraction**: Parsing GOAL.md to extract the "Minor Goal" section requires string parsing. If the format varies, the summary might be incomplete.
   - Mitigation: Use simple regex or string split, gracefully handle missing sections.

2. **Blocks count computation performance**: Computing blocked_by graph for each attention item could be slow with many work units.
   - Mitigation: Current scale is small. Can add caching or denormalization later if needed.

3. **Answer format for resume**: How should the answer be injected into the agent's context?
   - Decision: Include as a clear "Operator response: {answer}" message at the start of the resumed session. The agent SDK's resume mechanism will handle context restoration.

4. **Race condition on answer**: If an operator answers while the scheduler is about to dispatch, we might miss the answer.
   - Mitigation: Scheduler checks pending_answer after marking RUNNING. State transitions are atomic in SQLite.

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
