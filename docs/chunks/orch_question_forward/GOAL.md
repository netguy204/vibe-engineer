---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/agent.py
- src/orchestrator/scheduler.py
- src/orchestrator/models.py
- tests/test_orchestrator_agent.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/agent.py#create_question_intercept_hook
    implements: "PreToolUse hook for intercepting AskUserQuestion calls"
  - ref: src/orchestrator/agent.py#AgentRunner::run_phase
    implements: "Accepts question_callback and configures hook to capture questions"
  - ref: src/orchestrator/models.py#AgentResult
    implements: "Stores suspended=True and question data when hook fires"
  - ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
    implements: "Provides question_callback to run_phase for forwarding"
  - ref: src/orchestrator/scheduler.py#Scheduler::_handle_agent_result
    implements: "Transitions work unit to NEEDS_ATTENTION with question as attention_reason"
  - ref: tests/test_orchestrator_agent.py#TestQuestionInterceptHook
    implements: "Unit tests for hook creation and question extraction"
  - ref: tests/test_orchestrator_agent.py#TestRunPhaseWithQuestionCallback
    implements: "Unit tests for run_phase with question callback"
  - ref: tests/test_orchestrator_scheduler.py#TestQuestionForwardingFlow
    implements: "Integration tests for complete question forwarding flow"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after:
- ordering_field_clarity
---

# Chunk Goal

## Minor Goal

When background agents running under the orchestrator attempt to use the `AskUserQuestion` tool, forward those requests to the attention queue system rather than blocking or failing silently.

Currently, as discovered in the transcript audit, when background agents call `AskUserQuestion`, the tool returns an error (`is_error=True` with message "Answer questions?") and agents silently proceed without getting answers. This leads to unresolved uncertainty and potential implementation issues.

This chunk enables:
- Background agents to ask questions that surface in the attention queue
- Operators to answer agent questions via `ve orch answer` (from orch_attention_queue)
- Agent sessions to resume with the operator's answer injected
- Proper handling of uncertainty rather than silent failure

## Success Criteria

1. **AskUserQuestion calls are intercepted and forwarded**
   - When a background agent calls `AskUserQuestion`, the request is captured
   - The work unit transitions to NEEDS_ATTENTION status
   - The `attention_reason` field is populated with the question details
   - The agent session is paused (not terminated)

2. **Question context is preserved for operators**
   - Question text, options, and metadata are stored in the work unit
   - `ve orch attention` displays the question in the attention queue
   - Operators can see which agent asked what question and in what context

3. **Answers resume agent execution with context**
   - `ve orch answer <chunk> "response"` injects the answer into the session
   - The agent receives the answer as if the user had responded to `AskUserQuestion`
   - Work unit transitions: NEEDS_ATTENTION → RUNNING
   - Agent continues from where it paused, not from scratch

4. **Integration with Claude Code SDK**
   - Hook into Claude Code's tool handling to intercept `AskUserQuestion`
   - Use session resume capability with the answer injected as user message
   - Preserve session ID for resumption (from orch_attention_reason)

5. **Graceful handling of edge cases**
   - Multi-question tool calls are handled (all questions surfaced)
   - Agent timeout during NEEDS_ATTENTION doesn't lose context
   - Multiple agents asking questions simultaneously works correctly

## Dependencies

This chunk depends on:
- **orch_attention_queue** - Provides the attention queue infrastructure, `ve orch attention` and `ve orch answer` commands
- **orch_attention_reason** - Provides the `attention_reason` field and session_id tracking in work units

## Out of Scope

- Web dashboard for viewing/answering questions (Phase 5)
- Rich question UI beyond text answers
- Automatic answer generation or suggestions
- Question routing to specific operators