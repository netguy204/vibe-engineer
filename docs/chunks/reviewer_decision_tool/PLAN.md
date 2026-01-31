# Implementation Plan

## Approach

Replace the current text/YAML parsing approach for reviewer decisions with an explicit tool-call mechanism. The reviewer agent will be given access to a `ReviewDecision` tool that it must call to indicate its final decision. This makes the decision unambiguous and machine-readable.

The implementation follows the existing hook pattern used for `AskUserQuestion` interception (see `create_question_intercept_hook` in `src/orchestrator/agent.py`). We will:

1. Create a `ReviewDecision` tool definition that the agent can call
2. Create a hook that intercepts the tool call and captures the decision data
3. Return the captured decision in the `AgentResult` so the scheduler can route appropriately
4. Update the `/chunk-review` skill to instruct the reviewer to use the tool
5. Add in-session nudging when the reviewer completes without calling the tool

This approach:
- **Eliminates parsing ambiguity**: The decision comes from a structured tool call, not free-form text
- **Maintains backward compatibility**: Falls back gracefully if tool isn't called (nudges first, then escalates)
- **Follows existing patterns**: Uses the same hook infrastructure as question interception

Per docs/trunk/TESTING_PHILOSOPHY.md, we will write tests first for each behavioral component.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS new functionality within the orchestrator subsystem, specifically extending the agent execution and review handling patterns. The existing patterns (hooks for tool interception, AgentResult for capturing outcomes) will be reused.

## Sequence

### Step 1: Write failing tests for ReviewDecision tool capture

Create tests that verify:
- ReviewDecision tool call is captured by a hook
- Decision data (decision, summary, criteria_assessment) is extracted correctly
- AgentResult includes the captured review decision
- Missing tool call is detected

Location: `tests/test_orchestrator_scheduler.py` (add to existing TestReviewPhase class or new TestReviewDecisionTool class)

### Step 2: Add ReviewDecision data structures to models

Add structures to capture the tool call data:
- `ReviewToolDecision`: Pydantic model for the structured tool call data
- Update `AgentResult` to include optional `review_decision` field

Location: `src/orchestrator/models.py`

### Step 3: Create the ReviewDecision hook

Implement `create_review_decision_hook()` following the pattern of `create_question_intercept_hook()`:
- Match on a tool name like "ReviewDecision" or match a regex pattern
- Extract decision, summary, and optional criteria_assessment from tool_input
- Store captured data for return in AgentResult
- Return `SyncHookJSONOutput` with decision="allow" so the tool "succeeds" from the agent's perspective

Location: `src/orchestrator/agent.py`

### Step 4: Integrate hook into REVIEW phase execution

Update `AgentRunner.run_phase()` to:
- Accept an optional `review_decision_callback` parameter
- When phase is REVIEW, configure the ReviewDecision hook
- Return the captured decision in AgentResult

Location: `src/orchestrator/agent.py`

### Step 5: Write failing tests for in-session nudging

Create tests that verify:
- When reviewer completes without calling ReviewDecision tool, session is continued
- Nudge message prompts reviewer to call the tool
- After 3 nudges without tool call, escalate to NEEDS_ATTENTION

Location: `tests/test_orchestrator_scheduler.py`

### Step 6: Implement in-session nudging in scheduler

Update `_handle_review_result()` in scheduler to:
- Check if `AgentResult` has a `review_decision`
- If not, increment a nudge counter on the work unit
- If nudge_count < 3, resume the session with a nudge prompt
- If nudge_count >= 3, mark NEEDS_ATTENTION

This requires adding a `review_nudge_count` field to `WorkUnit`.

Location: `src/orchestrator/scheduler.py`, `src/orchestrator/models.py`

### Step 7: Update scheduler to route based on tool decision

Modify `_handle_review_result()` to:
- Prefer the decision from `AgentResult.review_decision` over file/log parsing
- Route work unit based on decision: APPROVE→COMPLETE, FEEDBACK→IMPLEMENT, ESCALATE→NEEDS_ATTENTION

Location: `src/orchestrator/scheduler.py`

### Step 8: Write failing tests for updated /chunk-review skill

Create tests that verify the skill template instructs the reviewer to use the ReviewDecision tool.

Location: `tests/test_templates.py` or similar

### Step 9: Update /chunk-review skill template

Modify the skill to:
- Inform reviewer that ReviewDecision tool is available
- Instruct reviewer to call the tool with their final decision
- Remove or de-emphasize the YAML output format (keep as fallback documentation)

Location: `src/templates/commands/chunk-review.md.jinja2`

### Step 10: Verify all existing tests pass

Run full test suite to ensure backward compatibility:
- Existing review decision parsing tests should still pass (fallback path)
- Phase advancement tests should work with new tool-based flow

Location: `tests/test_orchestrator_scheduler.py`

### Step 11: Add SQLite migration for review_nudge_count

If the new field requires a schema change, add a migration:
- Add `review_nudge_count` column to work_units table (default 0)

Location: `src/orchestrator/state.py`

---

**BACKREFERENCE COMMENTS**

When implementing, add:
```python
# Chunk: docs/chunks/reviewer_decision_tool - ReviewDecision tool for explicit review decisions
```

## Risks and Open Questions

1. **Tool definition mechanism**: The Claude Agent SDK may have specific requirements for how custom tools are defined. Need to verify if we need to provide a tool schema or if hook interception alone is sufficient.

2. **Tool name matching**: Need to determine the exact tool name the agent will use. Options:
   - Define a custom tool in the skill prompt
   - Use a naming convention the hook can match
   - May need to investigate Claude Agent SDK capabilities for custom tools

3. **Session resume behavior**: In-session nudging requires resuming with a new prompt. Need to verify the Claude Agent SDK supports this pattern cleanly (similar to how we resume after answering questions).

4. **Backward compatibility**: Some REVIEW phases may already be in progress when this change deploys. Need to ensure the fallback to YAML parsing still works for those cases.

## Deviations

*To be populated during implementation.*