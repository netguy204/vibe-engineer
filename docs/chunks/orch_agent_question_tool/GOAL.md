---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/agent.py
- tests/test_orchestrator_agent.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/agent.py#AgentRunner::run_phase
    implements: "Removed _is_error_result() heuristic call - SDK is_error flag is authoritative"
  - ref: src/orchestrator/agent.py#AgentRunner::run_commit
    implements: "Removed _is_error_result() heuristic call - SDK is_error flag is authoritative"
  - ref: src/orchestrator/agent.py#AgentRunner::resume_for_active_status
    implements: "Removed _is_error_result() heuristic call - SDK is_error flag is authoritative"
  - ref: tests/test_orchestrator_agent.py#TestErrorDetectionRemoval
    implements: "Tests verifying heuristic error detection is removed"
  - ref: tests/test_orchestrator_scheduler.py#TestVerboseSuccessNotMisinterpreted
    implements: "Integration tests for verbose success summaries not triggering NEEDS_ATTENTION"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
created_after:
- coderef_format_prompting
---

# Chunk Goal

## Minor Goal

Replace text-parsing heuristics for detecting agent questions with an explicit tool-based mechanism.

**Problem**: The orchestrator currently interprets agent output text to determine if the agent is asking a question. When an agent completes successfully but outputs a detailed summary, the orchestrator can misinterpret this as a question/failure. This happened with `coderef_format_prompting` where the agent's success summary was treated as an error, putting the work unit into NEEDS_ATTENTION despite successful completion.

**Solution**: Provide agents with an explicit `AskOperator` tool (or similar) that they must use when they need operator input. The orchestrator should only enter NEEDS_ATTENTION for questions when this tool is invoked, not based on parsing the agent's final text output.

This makes the question/completion distinction unambiguous and machine-verifiable rather than relying on fragile text parsing.

## Success Criteria

- Agent has access to an `AskOperator` tool (or equivalent) for requesting operator input
- Orchestrator only sets NEEDS_ATTENTION with a "question" reason when the tool is invoked
- Agent's final text output (success summaries, etc.) is never misinterpreted as a question
- The `ve orch answer` command still works to respond to tool-invoked questions
- Existing test coverage for attention/question flows updated to use the new mechanism
- Manual verification: an agent completing with a verbose summary does NOT trigger NEEDS_ATTENTION