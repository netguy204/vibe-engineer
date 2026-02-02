#!/usr/bin/env python3
"""Verify that AskUserQuestion hook interception works correctly.

This script tests whether the orchestrator's PreToolUse hook for AskUserQuestion
fires when an agent calls the tool. It creates a minimal test environment and
prompts the agent to ask a question.

Usage:
    uv run python scripts/verify_question_hook.py
"""

import asyncio
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import (
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
)

from orchestrator.agent import create_question_intercept_hook


async def verify_question_hook():
    """Run a minimal agent session that should trigger AskUserQuestion."""

    print("=" * 60)
    print("AskUserQuestion Hook Verification Test")
    print("=" * 60)

    # Track what happens
    captured_question_via_hook = None
    captured_question_via_message = None
    hook_fired = False

    def on_question(question_data: dict) -> None:
        nonlocal captured_question_via_hook, hook_fired
        hook_fired = True
        captured_question_via_hook = question_data
        print(f"\n✅ HOOK FIRED! Captured question:")
        print(f"   Question: {question_data.get('question', 'N/A')[:80]}")
        print(f"   Options: {len(question_data.get('options', []))} options")
        print(f"   Header: {question_data.get('header', 'N/A')}")

    # Create the hook
    hooks = create_question_intercept_hook(on_question)
    print(f"\n1. Created hook with matcher: {hooks['PreToolUse'][0]['matcher']}")

    # Create a temp directory for the agent to work in
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)

        # Set up agent options
        options = ClaudeAgentOptions(
            cwd=str(work_dir),
            allowed_tools=[
                "Read",
                "Write",
                "Edit",
                "Bash",
                "Glob",
                "Grep",
                "AskUserQuestion",  # Must be allowed
            ],
            permission_mode="bypassPermissions",
            model="claude-sonnet-4-20250514",  # Use a cheaper model for testing
            hooks=hooks,
        )

        # Prompt that should cause the agent to ask a question
        prompt = """You must immediately use the AskUserQuestion tool to ask me a simple question.

Use this exact format:
- question: "What color theme do you prefer?"
- header: "Theme"
- options: [{"label": "Dark", "description": "Dark mode"}, {"label": "Light", "description": "Light mode"}]
- multiSelect: false

Do NOT do anything else. Just call AskUserQuestion with a simple question.
This is a test to verify the tool works correctly."""

        print(f"\n2. Starting agent with prompt to trigger AskUserQuestion...")
        print(f"   Working directory: {work_dir}")
        print(f"   Hooks configured: {list(hooks.keys())}")

        session_id = None
        error = None
        tool_calls_seen = []

        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)

                async for message in client.receive_response():
                    # Track session ID
                    if isinstance(message, dict):
                        if message.get("type") == "init":
                            session_id = message.get("session_id")
                            print(f"\n3. Session started: {session_id[:20]}...")

                    # Track assistant messages for tool calls
                    # This is the fallback approach used for ReviewDecision
                    if isinstance(message, AssistantMessage):
                        if hasattr(message, "content") and message.content:
                            for block in message.content:
                                if hasattr(block, "name"):
                                    tool_calls_seen.append(block.name)
                                    print(f"\n   Tool call detected: {block.name}")

                                    # Fallback: Capture AskUserQuestion from message
                                    if block.name == "AskUserQuestion":
                                        tool_input = getattr(block, "input", {})
                                        print(f"   Input: {tool_input}")

                                        # Extract question data (same as hook would)
                                        questions = tool_input.get("questions", [])
                                        if questions:
                                            first_q = questions[0]
                                            captured_question_via_message = {
                                                "question": first_q.get("question", ""),
                                                "options": first_q.get("options", []),
                                                "header": first_q.get("header", ""),
                                                "multiSelect": first_q.get("multiSelect", False),
                                                "all_questions": questions,
                                            }
                                            print(f"\n   📦 Captured via AssistantMessage fallback:")
                                            print(f"      Question: {captured_question_via_message['question'][:60]}")

                    # Check for result
                    if isinstance(message, ResultMessage):
                        result_text = getattr(message, "result", None)
                        is_error = getattr(message, "is_error", False)
                        if is_error:
                            error = result_text
                            print(f"\n   Result (error): {result_text[:100] if result_text else 'N/A'}")
                        else:
                            print(f"\n   Result (success): {result_text[:100] if result_text else 'N/A'}")

        except Exception as e:
            error = str(e)
            print(f"\n❌ Exception: {e}")

        # Report results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)

        print(f"\nTool calls observed: {tool_calls_seen}")
        print(f"Hook fired: {hook_fired}")
        print(f"Question captured via hook: {captured_question_via_hook is not None}")
        print(f"Question captured via message: {captured_question_via_message is not None}")

        if "AskUserQuestion" in tool_calls_seen:
            if hook_fired:
                print("\n✅ SUCCESS: Hook intercepted AskUserQuestion!")
                print(f"   The question forwarding system works via hooks.")
                return True
            elif captured_question_via_message:
                print("\n⚠️  PARTIAL: Hook did NOT fire, but AssistantMessage fallback works!")
                print("   The fix should use AssistantMessage capture like ReviewDecision.")
                print("   This is the same pattern used for MCP tools.")
                return "fallback"
            else:
                print("\n❌ FAILURE: Agent called AskUserQuestion but neither hook nor fallback worked!")
                return False
        else:
            print("\n⚠️  Agent did not call AskUserQuestion tool.")
            print("   Cannot verify hook behavior. Try running again or check prompt.")
            return None


if __name__ == "__main__":
    result = asyncio.run(verify_question_hook())

    if result is True:
        print("\n\nHook verification PASSED (via hook)")
        sys.exit(0)
    elif result == "fallback":
        print("\n\nHook verification PASSED (via fallback)")
        print("FIX NEEDED: Implement AssistantMessage capture for AskUserQuestion")
        print("            (same pattern as ReviewDecision at agent.py:669-696)")
        sys.exit(0)
    elif result is False:
        print("\n\nHook verification FAILED")
        sys.exit(1)
    else:
        print("\n\nHook verification INCONCLUSIVE")
        sys.exit(2)
