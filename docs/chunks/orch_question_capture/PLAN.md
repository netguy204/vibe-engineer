# Implementation Plan

## Approach

This chunk fixes a bug where `AskUserQuestion` tool calls are not being intercepted by the orchestrator's PreToolUse hook, because **PreToolUse hooks don't fire for built-in tools**.

The solution applies the same pattern already proven for ReviewDecision MCP tool capture in `orch_reviewer_decision_mcp`:

1. **Capture from AssistantMessage content blocks** (lines 669-696 in agent.py)
2. **Detect ToolUseBlock with `block.name == "AskUserQuestion"`**
3. **Extract question data and invoke the question_callback**
4. **Break out of the message loop to suspend the agent**
5. **Return AgentResult with `suspended=True` and captured question**

The existing `create_question_intercept_hook()` remains as infrastructure, but won't fire for built-in tools. The functional capture moves to the message stream processing loop.

**Testing approach**: Following TESTING_PHILOSOPHY.md's test-driven development, we'll write failing tests first that simulate the message stream scenario where the agent calls AskUserQuestion. These tests must verify the behavior is correct regardless of whether the hook fires.

## Subsystem Considerations

- **docs/subsystems/orchestrator**: This chunk IMPLEMENTS part of the orchestrator's agent execution flow. The pattern for capturing tool calls from AssistantMessage content is already established (for ReviewDecision) and will be extended.

## Sequence

### Step 1: Write failing tests for AssistantMessage capture

Before modifying production code, add tests that verify AskUserQuestion capture from AssistantMessage content blocks. These tests should:

1. Create a `MessageStreamCaptureMock` (similar to existing `TestRunPhaseWithReviewDecisionCallback` at line 1453)
2. Yield an AssistantMessage with a ToolUseBlock where `block.name == "AskUserQuestion"`
3. Verify the question_callback is invoked
4. Verify the AgentResult has `suspended=True` and `question` populated

Location: `tests/test_orchestrator_agent.py`

The test should mimic the structure of `test_run_phase_captures_review_decision_from_message_stream` but for AskUserQuestion.

### Step 2: Add AskUserQuestion capture in the message loop

Modify `AgentRunner.run_phase()` to capture AskUserQuestion calls from AssistantMessage content, following the pattern at lines 669-696 for ReviewDecision.

Within the `if isinstance(message, AssistantMessage):` block, add logic:

```python
# Capture AskUserQuestion calls from message content
# Note: PreToolUse hooks don't fire for built-in tools
if (
    captured_question is None
    and hasattr(message, "content")
    and message.content
):
    for block in message.content:
        if hasattr(block, "name") and block.name == "AskUserQuestion":
            tool_input = getattr(block, "input", {})
            if tool_input:
                questions = tool_input.get("questions", [])
                if questions:
                    first_q = questions[0]
                    captured_question = {
                        "question": first_q.get("question", ""),
                        "options": first_q.get("options", []),
                        "header": first_q.get("header", ""),
                        "multiSelect": first_q.get("multiSelect", False),
                        "all_questions": questions,
                    }
                else:
                    captured_question = {
                        "question": "Agent asked a question (no details available)",
                        "options": [],
                        "header": "",
                        "multiSelect": False,
                        "all_questions": [],
                    }
                if question_callback:
                    question_callback(captured_question)
                break  # Only capture first call
```

Location: `src/orchestrator/agent.py`, inside `run_phase()`, around line 664-696

### Step 3: Verify tests pass

Run the tests to ensure the capture works:

```bash
uv run pytest tests/test_orchestrator_agent.py -v -k "AskUserQuestion"
```

### Step 4: Update verification script to confirm behavior

Run the verification script to see that it now reports successful capture:

```bash
uv run python scripts/verify_question_hook.py
```

Expected output should show either:
- "Hook fired: True" (if hooks do fire - unlikely)
- "Question captured via message: True" (our fix working)

The script should exit with code 0.

### Step 5: Add integration test for full flow

Add an integration test that verifies the complete flow:
1. Agent calls AskUserQuestion
2. Capture happens via AssistantMessage
3. AgentResult has suspended=True
4. Question data is correctly structured

This test should be in the existing `TestRunPhaseWithQuestionCallback` class but should simulate the real-world scenario where the hook doesn't fire.

Location: `tests/test_orchestrator_agent.py`

### Step 6: Add chunk backreference comment

Add a chunk backreference comment to the new code block:

```python
# Chunk: docs/chunks/orch_question_capture - Capture AskUserQuestion from AssistantMessage
```

## Dependencies

This chunk depends on work from:
- **orch_question_forward** (ACTIVE): The hook infrastructure and callback mechanism
- **orch_reviewer_decision_mcp** (ACTIVE): The pattern for AssistantMessage capture

No external libraries needed.

## Risks and Open Questions

1. **Hook vs. Message Capture Precedence**: If the hook somehow fires (different SDK behavior in future), both the hook AND the message capture could trigger. The code uses `captured_question is None` check to ensure only the first capture is used.

2. **Timing of ResultMessage**: Need to verify that the AssistantMessage with ToolUseBlock arrives before any ResultMessage that would terminate the loop. Based on ReviewDecision pattern, this is the expected SDK behavior.

3. **Verification script dependency**: The verification script depends on actual Claude API calls. If it fails due to API issues (not code issues), that's not a blocker for the implementation.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->