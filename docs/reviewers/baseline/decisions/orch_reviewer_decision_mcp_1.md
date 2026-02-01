---
decision: FEEDBACK
summary: 'FEEDBACK: Migrate orchestrator''s agent execution from `query()` to `ClaudeSDKClient`
  to enable hooks and custom MCP tools (ReviewDecision, AskUserQuestion)'
operator_review: good
---

## Assessment

The core implementation successfully migrates the agent execution layer:

1. **ClaudeSDKClient Migration**: Both `run_phase()` and `resume_for_active_status()` now use `ClaudeSDKClient` with the async context manager pattern (`async with ClaudeSDKClient(options) as client:`).

2. **MCP Tool Definition**: `ReviewDecision` is correctly defined using the `@tool` decorator with proper JSON schema for parameters (decision, summary, criteria_assessment, issues, reason).

3. **MCP Server Creation**: `create_orchestrator_mcp_server()` returns a valid SDK server config that gets attached to options during REVIEW phase.

4. **Hook Matcher Updated**: The `create_review_decision_hook()` matcher was updated to match `mcp__orchestrator__ReviewDecision` pattern.

5. **Deprecated Method Removed**: `run_commit()` was properly removed with a backreference comment explaining why.

6. **Test Coverage**: Comprehensive test classes added:
   - `TestMCPServerConfiguration` (4 tests)
   - Updated `TestReviewDecisionHook` with MCP tool naming
   - Updated `TestRunPhaseWithReviewDecisionCallback`
   - All 2054 tests pass

**Gap Found:**

The template `src/templates/commands/chunk-review.md.jinja2` was updated with ReviewDecision tool instructions (lines 73-83: "You MUST call the ReviewDecision tool", lines 197-202: "Do NOT complete the review without calling the ReviewDecision tool"), but the **rendered file** `.claude/commands/chunk-review.md` was NOT regenerated with `ve init`.

The rendered skill file (timestamp 16:58) predates the template update (timestamp 17:14) and lacks the critical instructions telling the reviewer agent to call the tool. When the orchestrator runs `/chunk-review`, it uses the rendered file, so reviewers won't be instructed to call the MCP tool.

## Decision Rationale

The core implementation meets all technical success criteria for the migration. However, the skill template regeneration was missed, which means the user-facing behavior (agents knowing to call the tool) won't work correctly until `ve init` is run.

This is a clear, fixable gap - run `ve init` to regenerate the skill file.

## Context

- Goal: Migrate orchestrator's agent execution from `query()` to `ClaudeSDKClient` to enable hooks and custom MCP tools (ReviewDecision, AskUserQuestion)
- Linked artifacts: parent_chunk: reviewer_decision_tool
