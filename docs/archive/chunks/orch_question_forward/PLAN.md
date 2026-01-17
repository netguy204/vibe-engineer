<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements the critical integration between background agents' `AskUserQuestion` tool calls and the orchestrator's attention queue system. Currently, background agents calling `AskUserQuestion` receive an error and proceed without answers. This chunk makes questions surface properly for operator response.

**Key technical choices:**

1. **PreToolUse hook for AskUserQuestion interception**: The Claude Agent SDK provides `hooks` option with `PreToolUse` event type. We configure a hook that matches the `AskUserQuestion` tool and:
   - Extracts the question data from `tool_input`
   - Returns a hook result with `decision: "block"` to prevent the tool from executing
   - Returns a custom `reason` explaining the question is queued for the operator
   - Signals the agent loop should stop via `stopReason`

2. **Callback-based question capture**: The `AgentRunner.run_phase()` method accepts an optional `question_callback: Callable[[dict], None]` that receives extracted question data when the hook intercepts `AskUserQuestion`. This allows the scheduler to capture the question and store it in the work unit's `attention_reason`.

3. **Session suspension with preserved context**: When the hook fires:
   - The session_id is already captured from the init message
   - The hook stops agent iteration with the session in a resumable state
   - The work unit transitions to NEEDS_ATTENTION with question context
   - When operator answers, session resumes with answer injected (already implemented in orch_attention_queue)

4. **Question data structure**: The extracted question includes:
   - `question`: The question text
   - `options`: Array of option objects (label, description)
   - `header`: Short label for the question
   - `multiSelect`: Whether multiple selections allowed

**Building on existing code:**
- `AgentRunner.run_phase()` in `src/orchestrator/agent.py` - Add hooks configuration
- `AgentResult` model with `suspended` and `question` fields - Already exists
- `Scheduler._handle_agent_result()` - Already handles suspended results
- `ve orch answer` command - Already injects answers on resume

**Testing approach per docs/trunk/TESTING_PHILOSOPHY.md:**
- Unit tests verify hook is configured when callback provided
- Unit tests verify question extraction from tool_input
- Unit tests verify AgentResult is marked suspended with question data
- Integration tests verify the full flow: question → NEEDS_ATTENTION → answer → resume

## Subsystem Considerations

No existing subsystems are directly relevant to this chunk. The orchestrator is a new major component that may become a subsystem itself once stable.

## Sequence

### Step 1: Add PreToolUse hook helper for AskUserQuestion

Create a helper function in `src/orchestrator/agent.py` that builds a PreToolUse hook configuration for intercepting `AskUserQuestion`:

```python
def create_question_intercept_hook(
    on_question: Callable[[dict, str], None]  # (question_data, session_id) -> None
) -> dict:
    """Create a PreToolUse hook that intercepts AskUserQuestion calls.

    When AskUserQuestion is called, extracts the question data and calls
    on_question callback, then returns a result that blocks the tool and
    stops the agent loop.
    """
```

The hook:
1. Matches tool_name == "AskUserQuestion"
2. Extracts question/options/header/multiSelect from tool_input
3. Calls the callback with extracted data
4. Returns `SyncHookJSONOutput` with:
   - `decision: "block"` (prevent tool execution)
   - `stopReason: "question_queued"` (stop agent iteration)
   - `reason: "Question forwarded to attention queue for operator response"`
   - `hookSpecificOutput` with `permissionDecision: "deny"`

Location: src/orchestrator/agent.py

### Step 2: Modify run_phase to accept question callback and configure hook

Update `AgentRunner.run_phase()` signature to accept:

```python
async def run_phase(
    self,
    chunk: str,
    phase: WorkUnitPhase,
    worktree_path: Path,
    resume_session_id: Optional[str] = None,
    answer: Optional[str] = None,
    log_callback: Optional[callable] = None,
    question_callback: Optional[Callable[[dict], None]] = None,  # NEW
) -> AgentResult:
```

When `question_callback` is provided:
1. Create the PreToolUse hook using the helper from Step 1
2. Configure `ClaudeAgentOptions` with the hook
3. When hook fires, capture session_id and question data
4. Mark result as `suspended=True` with question data

The hook callback stores the question data in a local variable, and after the agent loop completes (due to stopReason), the method returns an AgentResult with `suspended=True` and `question` populated.

Location: src/orchestrator/agent.py

### Step 3: Update scheduler to provide question callback

Modify `Scheduler._run_work_unit()` to:
1. Create a local variable to capture question data
2. Define a callback that captures question data
3. Pass the callback to `agent_runner.run_phase()`
4. After run_phase returns, if question was captured, it's available in the AgentResult

The existing `_handle_agent_result()` already handles `result.suspended=True` correctly - it sets `attention_reason` from `result.question`. Verify this flow works with the new hook-based suspension.

Location: src/orchestrator/scheduler.py

### Step 4: Update AgentResult to ensure question data flows correctly

Verify the `AgentResult` model has adequate fields:

```python
class AgentResult(BaseModel):
    completed: bool
    suspended: bool = False
    session_id: Optional[str] = None
    question: Optional[dict] = None  # Question data if suspended
    error: Optional[str] = None
```

The `question` dict should match the AskUserQuestion tool input structure for display in `ve orch attention`.

Location: src/orchestrator/models.py

### Step 5: Write tests for hook creation and question extraction

Create tests in `tests/test_orchestrator_agent.py`:

```python
class TestQuestionInterceptHook:
    def test_create_hook_returns_valid_hook_config(self):
        """Hook config has correct structure for PreToolUse."""

    async def test_hook_extracts_question_data(self):
        """Hook callback receives question text and options."""

    async def test_hook_returns_block_decision(self):
        """Hook output blocks tool execution."""

    async def test_hook_sets_stop_reason(self):
        """Hook output sets stopReason to terminate loop."""
```

Location: tests/test_orchestrator_agent.py

### Step 6: Write tests for run_phase with question callback

Add tests to verify `run_phase` behavior:

```python
class TestRunPhaseWithQuestionCallback:
    @pytest.mark.asyncio
    async def test_run_phase_with_callback_configures_hook(self):
        """When callback provided, options include PreToolUse hook."""

    @pytest.mark.asyncio
    async def test_run_phase_captures_question_on_intercept(self):
        """When AskUserQuestion intercepted, result has suspended=True and question."""

    @pytest.mark.asyncio
    async def test_run_phase_without_callback_no_hook(self):
        """When no callback, options don't include hook."""
```

Location: tests/test_orchestrator_agent.py

### Step 7: Write integration test for question forwarding flow

Add integration test that verifies the full flow:

1. Set up a mock agent that will call AskUserQuestion
2. Inject a work unit and start it running
3. Verify work unit transitions to NEEDS_ATTENTION
4. Verify attention_reason contains the question text
5. Answer the question via `ve orch answer`
6. Verify work unit transitions to READY with pending_answer
7. Verify on resume, the answer is available in the agent prompt

This may require mocking the Claude Agent SDK to simulate the AskUserQuestion tool call.

Location: tests/test_orchestrator_scheduler.py

### Step 8: Update attention reason formatting for questions

Ensure that when a question is captured, the `attention_reason` includes:
- The question text prominently
- Indication it's a question (vs an error)
- Optionally the available options

Format: `Question: {question_text}`

This is already partially implemented in `_handle_agent_result()`. Verify and enhance if needed.

Location: src/orchestrator/scheduler.py

### Step 9: Test with real agent (manual verification)

Manually test by:
1. Starting orchestrator: `ve orch start`
2. Creating a test chunk that will ask a question
3. Injecting: `ve orch inject test_chunk`
4. Observing the agent run and ask a question
5. Checking `ve orch attention` shows the question
6. Answering: `ve orch answer test_chunk "my answer"`
7. Verifying the agent resumes with the answer

Document any deviations discovered during manual testing.

## Dependencies

**Chunks:**
- `orch_attention_queue` (ACTIVE) - Provides attention queue infrastructure, `ve orch answer` command
- `orch_attention_reason` (ACTIVE) - Provides `attention_reason` field storage

**External libraries:**
- `claude-agent-sdk` - Already installed, provides hook mechanism

## Risks and Open Questions

1. **Hook termination behavior**: Need to verify that returning `stopReason` from a PreToolUse hook actually stops the agent loop in a resumable state. The SDK documentation isn't explicit about this.
   - Mitigation: Test with mock SDK first, then verify with real SDK.

2. **Session resumability after hook-based stop**: When the hook stops execution, the session should be resumable. Need to verify the session_id captured from init message works for resume.
   - Mitigation: Test resume flow explicitly.

3. **Multi-question tool calls**: The AskUserQuestion tool supports 1-4 questions. Need to decide how to handle:
   - Option A: Forward all questions to attention queue as single item
   - Option B: Fail if multiple questions (not currently supported)
   - Decision: Option A - bundle all questions together in attention_reason

4. **Hook configuration lifecycle**: The hook is configured per-query. Need to ensure it's properly scoped and doesn't persist across phases.
   - Already correct: Each `run_phase` creates fresh options.

5. **Answer format for AskUserQuestion**: The tool expects structured responses. When injecting an answer on resume, format needs to match what the agent expects.
   - Current approach: Inject as plain text "User answer: {text}". Agent should understand.

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