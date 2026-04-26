---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/agent.py
- src/orchestrator/scheduler.py
- src/orchestrator/models.py
- src/orchestrator/state.py
- src/templates/commands/chunk-review.md.jinja2
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/models.py#ReviewToolDecision
    implements: "Pydantic model capturing structured data from ReviewDecision tool calls"
  - ref: src/orchestrator/models.py#AgentResult
    implements: "Extended with review_decision field for captured tool call data"
  - ref: src/orchestrator/models.py#WorkUnit
    implements: "Extended with review_nudge_count field tracking nudge attempts"
  - ref: src/orchestrator/agent.py#create_review_decision_hook
    implements: "PreToolUse hook that intercepts ReviewDecision tool calls and captures decision data"
  - ref: src/orchestrator/agent.py#AgentRunner::run_phase
    implements: "Updated to accept review_decision_callback for REVIEW phase tool interception"
  - ref: src/orchestrator/scheduler.py#Scheduler::_handle_review_result
    implements: "Review result handling with tool-based decision priority and in-session nudging"
  - ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
    implements: "Sets up review_decision_callback during REVIEW phase dispatch"
  - ref: src/orchestrator/state.py#StateStore::_migrate_v10
    implements: "Schema migration adding review_nudge_count column to work_units table"
  - ref: src/templates/commands/chunk-review.md.jinja2
    implements: "Updated reviewer skill instructions requiring ReviewDecision tool usage"
  - ref: tests/test_orchestrator_scheduler_review.py#TestReviewDecisionTool
    implements: "Test class verifying tool submission, nudging, and escalation behavior"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- orch_plan_merge_conflict
- orch_tail_command
---

# Chunk Goal

## Minor Goal

The reviewer agent submits its final decision by calling a dedicated `ReviewDecision` tool rather than emitting parseable text or a YAML file. The orchestrator reads the decision from the tool call result.

**Why a tool, not text parsing:** Text/YAML parsing is brittle. When the orchestrator cannot parse a decision format, it has no safe default — silently approving a FEEDBACK decision lets work with unmet criteria proceed to COMPLETE. A tool call is unambiguous and machine-readable:

```python
# Reviewer calls this tool to submit decision
ReviewDecision(
    decision="FEEDBACK",  # APPROVE | FEEDBACK | ESCALATE
    summary="Missing follow mode tests",
    criteria_assessment=[...]
)
```

If the reviewer completes the session without calling the tool, the orchestrator nudges it to do so; after three nudges without a tool call, the work unit escalates to NEEDS_ATTENTION.

## Success Criteria

- New `ReviewDecision` tool is available to the reviewer agent during REVIEW phase
- Tool accepts: `decision` (APPROVE/FEEDBACK/ESCALATE), `summary`, and optional structured feedback
- Orchestrator reads decision from tool call result, not from text parsing
- If reviewer completes without calling the tool, continue the same session and nudge the reviewer to call the tool with its final decision
- After 3 nudge attempts without a tool call, escalate to NEEDS_ATTENTION
- Update `/chunk-review` skill to instruct reviewer to use the tool
- Tests verify: tool submission works, missing tool call triggers in-session nudge, 3 failed nudges escalates to NEEDS_ATTENTION, decision routing (APPROVE→COMPLETE, FEEDBACK→IMPLEMENT, ESCALATE→NEEDS_ATTENTION)
- Existing tests pass