---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/agent.py
- tests/test_orchestrator_agent_stream.py
code_references:
  - ref: src/orchestrator/agent.py#AgentRunner::run_phase
    implements: "AskUserQuestion capture from AssistantMessage content blocks when PreToolUse hooks don't fire"
  - ref: tests/test_orchestrator_agent_stream.py#TestAskUserQuestionMessageStreamCapture
    implements: "Unit tests verifying message stream capture of AskUserQuestion calls"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- orch_inject_filter_done
- orch_worktree_retain
---

# Chunk Goal

## Minor Goal

Capture AskUserQuestion tool calls from AssistantMessage content instead of relying on PreToolUse hooks, which don't fire for built-in tools.

**The problem:** The `orch_question_forward` chunk implemented a PreToolUse hook to intercept AskUserQuestion calls and forward them to the attention queue. However, testing reveals that PreToolUse hooks **don't fire for built-in tools** (same limitation discovered for MCP tools in `orch_reviewer_decision_mcp`).

Evidence from verification script (`scripts/verify_question_hook.py`):
```
Tool calls observed: ['AskUserQuestion']
Hook fired: False
Question captured via hook: False
Question captured via message: True
```

Historical evidence from `.ve/chunks/deferred_worktree_creation/log/plan.txt`:
```
Line 7: ToolUseBlock(name='AskUserQuestion', input={...})
Line 8: ToolResultBlock(content='Answer questions?', is_error=True)
```
The agent called AskUserQuestion, received an error, and continued executing instead of being suspended.

**The solution:** Apply the same pattern used for ReviewDecision at `agent.py:669-696`:
1. Capture AskUserQuestion calls from AssistantMessage content blocks
2. Extract question data when `block.name == "AskUserQuestion"`
3. Break out of the message loop to suspend the agent
4. Return `AgentResult(suspended=True, question=captured_question)`

## Success Criteria

1. **AskUserQuestion captured from AssistantMessage**
   - When an agent calls AskUserQuestion, the call is detected in AssistantMessage content
   - Question data (question text, options, header, multiSelect) is extracted
   - The `question_callback` is invoked with the extracted data

2. **Agent session suspends correctly**
   - After AskUserQuestion is detected, the message loop exits
   - `AgentResult.suspended = True` is returned
   - `AgentResult.question` contains the extracted question data
   - `AgentResult.session_id` is preserved for resume

3. **Verification script passes**
   - `scripts/verify_question_hook.py` shows "Hook fired: True" OR "Question captured via message: True"
   - Exit code 0 confirms the fix works

4. **Integration with attention queue**
   - Scheduler receives the suspended result with question
   - Work unit transitions to NEEDS_ATTENTION with question in attention_reason
   - Existing `orch_question_forward` flow works end-to-end

5. **Tests verify the capture**
   - Unit test: AssistantMessage with AskUserQuestion block triggers capture
   - Integration test: Full flow from agent call to NEEDS_ATTENTION status

## Related Chunks

This chunk follows the pattern established in `orch_reviewer_decision_mcp`:
- That chunk discovered PreToolUse hooks don't fire for MCP tools
- It implemented AssistantMessage capture as a workaround (lines 669-696)
- This chunk applies the same pattern for built-in tools (AskUserQuestion)

The `orch_question_forward` chunk's hook infrastructure remains valid but unused:
- `create_question_intercept_hook()` still exists but hooks don't fire
- The callback mechanism and `AgentResult.suspended` flow are correct
- Only the capture method changes (AssistantMessage instead of hook)