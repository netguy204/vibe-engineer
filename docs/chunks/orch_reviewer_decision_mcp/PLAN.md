<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Migrate `AgentRunner` from using `query()` to `ClaudeSDKClient` to enable hooks and custom tools. The migration follows a layered approach:

1. **Define ReviewDecision as an MCP tool** using the `@tool` decorator and `create_sdk_mcp_server()` pattern documented in the Claude Agent SDK
2. **Migrate `run_phase()` to ClaudeSDKClient** which supports hooks and custom tools (unlike `query()` which doesn't)
3. **Preserve existing behavior** - The hooks for sandbox enforcement and question interception are already defined but never fire; after migration they will work
4. **Add integration tests** verifying both hook-based interception and MCP tool invocation

The key SDK difference (per [Agent SDK docs](https://platform.claude.com/docs/en/agent-sdk/python)):

| Feature | `query()` | `ClaudeSDKClient` |
|---------|-----------|-------------------|
| Hooks | ❌ Not supported | ✅ Supported |
| Custom Tools | ❌ Not supported | ✅ Supported |
| Session Continuity | ❌ New session each time | ✅ Maintains conversation |

MCP tool naming convention: Tools are named `mcp__<server>__<action>`, e.g., `mcp__orchestrator__ReviewDecision`.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk USES the orchestrator subsystem - it modifies the agent execution layer (`AgentRunner`) which is a core component. The changes are compliant with the subsystem's scope ("Agent scheduling" and "Phase execution").

## Sequence

### Step 1: Define ReviewDecision MCP tool

Create the ReviewDecision tool using the `@tool` decorator. This tool receives the reviewer's decision and returns a confirmation.

Location: `src/orchestrator/agent.py`

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool(
    "ReviewDecision",
    "Submit the final review decision for the implementation",
    {
        "decision": str,  # APPROVE, FEEDBACK, or ESCALATE
        "summary": str,   # Brief summary of the review
        "criteria_assessment": list,  # Optional structured feedback
        "issues": list,   # Optional issues for FEEDBACK
        "reason": str,    # Optional reason for ESCALATE
    }
)
async def review_decision_tool(args: dict) -> dict:
    """Handle ReviewDecision tool calls from the reviewer agent."""
    # The actual decision capture happens via the hook
    return {
        "content": [{
            "type": "text",
            "text": f"Review decision '{args['decision']}' recorded."
        }]
    }
```

Create the MCP server:

```python
def create_orchestrator_mcp_server():
    """Create MCP server with orchestrator tools."""
    return create_sdk_mcp_server(
        name="orchestrator",
        version="1.0.0",
        tools=[review_decision_tool]
    )
```

### Step 2: Update imports in agent.py

Add the new SDK imports required for `ClaudeSDKClient` and MCP tools:

```python
from claude_agent_sdk import (
    query,  # Keep for backwards compatibility in deprecated methods
    ClaudeSDKClient,
    tool,
    create_sdk_mcp_server,
)
```

### Step 3: Refactor run_phase() to use ClaudeSDKClient

Replace the `query()` call with `ClaudeSDKClient` context manager pattern. The key changes:

1. Create client with options including MCP servers and hooks
2. Use `async with ClaudeSDKClient(options) as client:` for session management
3. Call `client.query(prompt)` to send the request
4. Iterate `async for message in client.receive_response():` to process messages
5. Handle resume by passing `resume=session_id` in options

```python
async def run_phase(self, ...):
    # Build options with MCP servers for custom tools
    options = ClaudeAgentOptions(
        cwd=str(worktree_path),
        permission_mode="bypassPermissions",
        max_turns=100,
        setting_sources=["project"],
        env=env,
        hooks=all_hooks,  # Hooks now work with ClaudeSDKClient
    )

    # Add MCP server for REVIEW phase
    if phase == WorkUnitPhase.REVIEW:
        mcp_server = create_orchestrator_mcp_server()
        options.mcp_servers = {"orchestrator": mcp_server}
        options.allowed_tools.append("mcp__orchestrator__ReviewDecision")

    # Resume support
    if resume_session_id:
        options.resume = resume_session_id

    async with ClaudeSDKClient(options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            # Process messages (same logic as before)
```

### Step 4: Update hook integration for ReviewDecision

The existing `create_review_decision_hook()` intercepts the tool call. With ClaudeSDKClient:

1. The MCP tool `mcp__orchestrator__ReviewDecision` is callable by the agent
2. The PreToolUse hook fires BEFORE the tool executes
3. The hook captures the decision data and calls the callback
4. The hook returns `decision="allow"` so the tool executes and the agent sees success

Update the hook matcher to match the MCP tool name:

```python
hook_matcher: HookMatcher = {
    "matcher": re.compile(r"^mcp__orchestrator__ReviewDecision$", re.IGNORECASE),
    "hooks": [hook_handler],
    "timeout": None,
}
```

### Step 5: Remove deprecated run_commit() method

Delete the unused `run_commit()` method from `AgentRunner`. It was deprecated when the scheduler switched to `WorktreeManager.commit_changes()` for mechanical commits.

Location: `src/orchestrator/agent.py`

Also remove its tests from `tests/test_orchestrator_agent.py`:
- `test_run_commit_includes_setting_sources`
- `test_run_commit_configures_sandbox_hook`

### Step 6: Migrate resume_for_active_status()

This method also uses `query()`. Apply the same migration pattern:

1. Replace `query()` with `ClaudeSDKClient`
2. No MCP tools required
3. Hooks for sandbox enforcement will now work

### Step 7: Update session ID extraction

With `ClaudeSDKClient`, session IDs come from different message types:

```python
# After connect/query
async for message in client.receive_response():
    if isinstance(message, ResultMessage):
        session_id = message.session_id
        # ... rest of handling
```

### Step 8: Write tests for hook and tool integration

Add tests in `tests/test_orchestrator_scheduler.py`:

1. **Test MCP tool is callable**: Verify reviewer agent can call `mcp__orchestrator__ReviewDecision`
2. **Test hook fires**: Verify PreToolUse hook intercepts the tool call and captures decision
3. **Test AskUserQuestion hook works**: Verify question interception now functions
4. **Test sandbox hook works**: Verify sandbox enforcement hook prevents escapes

Location: `tests/test_orchestrator_scheduler.py`

```python
class TestClaudeSDKClientMigration:
    """Tests verifying the query() to ClaudeSDKClient migration."""

    @pytest.mark.asyncio
    async def test_review_decision_tool_callable(self, ...):
        """Reviewer agent can call the ReviewDecision MCP tool."""

    @pytest.mark.asyncio
    async def test_question_hook_fires(self, ...):
        """AskUserQuestion hook now fires and captures questions."""
```

### Step 9: Update chunk-review skill template

Ensure the `/chunk-review` skill instructions reference the correct tool name:

Location: `src/templates/commands/chunk-review.md.jinja2`

Update any references from `ReviewDecision` to `mcp__orchestrator__ReviewDecision` if needed, or document that the tool can be called as either (if the SDK supports both).

## Dependencies

- Claude Agent SDK version must support `ClaudeSDKClient`, `@tool` decorator, and `create_sdk_mcp_server()` (documented in current SDK reference)
- No new external libraries required - features are already in `claude-agent-sdk`

## Risks and Open Questions

1. **Session continuity behavior**: `ClaudeSDKClient` maintains sessions - need to verify nudging (resuming with pending_answer) works correctly with session resume
2. **MCP tool naming**: The SDK documentation shows tools named `mcp__<server>__<action>` - need to verify exact naming required for hook matchers
3. **Hook timing**: With MCP tools, verify PreToolUse hook fires BEFORE the MCP tool handler executes, allowing decision capture

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->