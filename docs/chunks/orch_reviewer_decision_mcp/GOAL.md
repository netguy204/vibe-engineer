---
status: ACTIVE
ticket: null
parent_chunk: reviewer_decision_tool
code_paths:
- src/orchestrator/agent.py
- src/orchestrator/scheduler.py
- src/templates/commands/chunk-review.md.jinja2
- tests/test_orchestrator_scheduler.py
- tests/test_orchestrator_agent.py
code_references:
  - ref: src/orchestrator/agent.py#review_decision_tool
    implements: "ReviewDecision MCP tool defined via @tool decorator"
  - ref: src/orchestrator/agent.py#create_orchestrator_mcp_server
    implements: "Creates MCP server with orchestrator tools for REVIEW phase"
  - ref: src/orchestrator/agent.py#AgentRunner::run_phase
    implements: "Main phase execution migrated from query() to ClaudeSDKClient"
  - ref: src/orchestrator/agent.py#AgentRunner::resume_for_active_status
    implements: "Session resume migrated from query() to ClaudeSDKClient"
  - ref: src/orchestrator/agent.py#create_review_decision_hook
    implements: "Hook updated to match MCP tool naming convention (mcp__orchestrator__ReviewDecision)"
  - ref: tests/test_orchestrator_agent_review.py#TestMCPServerConfiguration
    implements: "Tests for MCP server configuration during REVIEW phase"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after: ["orch_dashboard_live_tail", "reviewer_decision_tool"]
---

# Chunk Goal

## Minor Goal

Migrate the orchestrator's agent execution from `query()` to `ClaudeSDKClient` to enable hooks and custom tools.

**The problem:** The orchestrator uses `query()` for agent execution, but per the SDK documentation:

| Feature | `query()` | `ClaudeSDKClient` |
|---------|-----------|-------------------|
| Hooks | ❌ Not supported | ✅ Supported |
| Custom Tools | ❌ Not supported | ✅ Supported |

This explains two broken features:

1. **AskUserQuestion interception never works**: The hook to capture agent questions and route them to the attention queue never fires. Questions have never reached the operator.

2. **ReviewDecision tool can't be called**: The custom tool doesn't exist (hooks can't create tools), and even if it did, the hook to intercept it wouldn't fire.

**The solution:** Migrate `AgentRunner` from `query()` to `ClaudeSDKClient`:

```python
from claude_agent_sdk import ClaudeSDKClient, tool, create_sdk_mcp_server

# Define custom tools with @tool decorator
@tool("ReviewDecision", "Submit review decision", {"decision": str, "summary": str})
async def review_decision(args: dict) -> dict:
    # Handler receives calls directly - no hook needed
    return {"content": [{"type": "text", "text": "Decision recorded"}]}

# Create MCP server for custom tools
orchestrator_tools = create_sdk_mcp_server(name="orchestrator", tools=[review_decision])

# Use ClaudeSDKClient which supports hooks
async with ClaudeSDKClient(options) as client:
    await client.query(prompt)
    async for message in client.receive_response():
        # Process messages
```

With `ClaudeSDKClient`:
- Hooks work → AskUserQuestion interception functions
- Custom tools via MCP → ReviewDecision is callable
- Session continuity available if needed for nudging

## Success Criteria

- `AgentRunner.run_phase()` uses `ClaudeSDKClient` instead of `query()`
- `AskUserQuestion` hook fires and questions reach the attention queue
- `ReviewDecision` custom tool is defined via `@tool` decorator and MCP server
- Reviewer agent can call `ReviewDecision` and decision is captured/routed correctly
- Existing phase execution behavior preserved (GOAL, PLAN, IMPLEMENT, REVIEW, COMPLETE)
- Session resume functionality works with `ClaudeSDKClient`
- Existing tests pass; add tests verifying both tool interceptions work
- Sandbox enforcement hooks continue to function