# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_reviewer_decision_mcp - Updated tests for ClaudeSDKClient migration
"""Tests for the orchestrator agent runner - Review Decision tests."""

import pytest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.agent import (
    AgentRunner,
    AgentRunnerError,
    PHASE_SKILL_FILES,
    create_log_callback,
    create_question_intercept_hook,
    create_review_decision_hook,
    create_sandbox_enforcement_hook,
    create_orchestrator_mcp_server,
    review_decision_tool,
    _load_skill_content,
    _is_sandbox_violation,
    _merge_hooks,
)
from orchestrator.models import AgentResult, ReviewToolDecision, WorkUnitPhase


class MockClaudeSDKClient:
    """Mock for ClaudeSDKClient that supports async context manager pattern.

    This mock simulates the ClaudeSDKClient behavior:
    - Async context manager (__aenter__/__aexit__)
    - query() method to send prompts
    - receive_response() async iterator for messages
    """
    # Class-level storage for test introspection
    last_instance = None
    all_instances = []

    def __init__(self, options=None):
        self.options = options
        self._messages = []
        self._exception = None
        self._query_prompt = None
        # Store instance for test introspection
        MockClaudeSDKClient.last_instance = self
        MockClaudeSDKClient.all_instances.append(self)

    @classmethod
    def reset(cls):
        """Reset class-level state between tests."""
        cls.last_instance = None
        cls.all_instances = []

    def set_messages(self, messages):
        """Configure messages to yield from receive_response()."""
        self._messages = messages

    def set_exception(self, exc):
        """Configure an exception to raise during receive_response()."""
        self._exception = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def query(self, prompt):
        """Record the query prompt."""
        self._query_prompt = prompt

    async def receive_response(self):
        """Yield configured messages or raise configured exception."""
        if self._exception:
            raise self._exception
        for msg in self._messages:
            yield msg


def create_mock_claude_sdk_client(messages=None, exception=None):
    """Factory to create a configured MockClaudeSDKClient.

    Args:
        messages: List of messages to yield from receive_response()
        exception: Exception to raise during receive_response()

    Returns:
        A MockClaudeSDKClient class that can be used with patch()
    """
    # Reset class-level state
    MockClaudeSDKClient.reset()

    class ConfiguredMock(MockClaudeSDKClient):
        def __init__(self, options=None):
            super().__init__(options)
            if messages:
                self._messages = messages
            if exception:
                self._exception = exception

    return ConfiguredMock


@pytest.fixture
def project_dir(tmp_path):
    """Create a project directory with skill files for testing."""
    # Create .agents/skills directory structure (canonical location)
    skills_dir = tmp_path / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    # Create .claude/commands directory for backwards-compat symlinks
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Create skill files with minimal content
    skill_content = """---
description: Test skill
---

## Instructions

This is a test skill for {phase}.
"""
    for phase, skill_name in PHASE_SKILL_FILES.items():
        # Create canonical skill directory and SKILL.md
        skill_dir = skills_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            skill_content.format(phase=phase.value)
        )
        # Create backwards-compat symlink in .claude/commands/
        symlink_path = commands_dir / f"{skill_name}.md"
        symlink_path.symlink_to(skill_dir / "SKILL.md")

    return tmp_path


# Chunk: docs/chunks/reviewer_decision_tool - ReviewDecision tool for explicit review decisions
class TestReviewDecisionHook:
    """Tests for ReviewDecision tool interception hook."""

    def test_create_hook_returns_valid_hook_config(self):
        """Hook config has correct structure for PreToolUse."""
        captured = []
        hooks = create_review_decision_hook(lambda d: captured.append(d))

        assert "PreToolUse" in hooks
        assert len(hooks["PreToolUse"]) == 1

        hook_matcher = hooks["PreToolUse"][0]
        # Matcher is a regex pattern for case-insensitive MCP tool name matching
        # Chunk: docs/chunks/orch_reviewer_decision_mcp - Updated to MCP tool naming
        assert hook_matcher["matcher"].pattern == "^mcp__orchestrator__ReviewDecision$"
        assert hook_matcher["hooks"] is not None
        assert len(hook_matcher["hooks"]) == 1

    @pytest.mark.asyncio
    async def test_hook_extracts_decision_data(self):
        """Hook callback receives decision, summary, and structured data."""
        captured = []
        hooks = create_review_decision_hook(lambda d: captured.append(d))

        hook_handler = hooks["PreToolUse"][0]["hooks"][0]

        # Simulate PreToolUseHookInput for ReviewDecision
        hook_input = {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript",
            "cwd": "/tmp/work",
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__orchestrator__ReviewDecision",
            "tool_input": {
                "decision": "APPROVE",
                "summary": "Implementation meets all requirements",
                "criteria_assessment": [
                    {"criterion": "Tests pass", "status": "satisfied"}
                ],
            },
        }

        result = await hook_handler(hook_input, None, {"signal": None})

        # Verify callback was called with extracted data
        assert len(captured) == 1
        decision_data = captured[0]
        assert isinstance(decision_data, ReviewToolDecision)
        assert decision_data.decision == "APPROVE"
        assert decision_data.summary == "Implementation meets all requirements"
        assert len(decision_data.criteria_assessment) == 1

    @pytest.mark.asyncio
    async def test_hook_extracts_feedback_with_issues(self):
        """Hook extracts issues for FEEDBACK decisions."""
        captured = []
        hooks = create_review_decision_hook(lambda d: captured.append(d))

        hook_handler = hooks["PreToolUse"][0]["hooks"][0]

        hook_input = {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript",
            "cwd": "/tmp/work",
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__orchestrator__ReviewDecision",
            "tool_input": {
                "decision": "FEEDBACK",
                "summary": "Missing error handling",
                "issues": [
                    {
                        "location": "src/main.py",
                        "concern": "No try/except",
                        "suggestion": "Add error handling",
                    }
                ],
            },
        }

        result = await hook_handler(hook_input, None, {"signal": None})

        assert len(captured) == 1
        decision_data = captured[0]
        assert decision_data.decision == "FEEDBACK"
        assert len(decision_data.issues) == 1
        assert decision_data.issues[0]["location"] == "src/main.py"

    @pytest.mark.asyncio
    async def test_hook_extracts_escalate_with_reason(self):
        """Hook extracts reason for ESCALATE decisions."""
        captured = []
        hooks = create_review_decision_hook(lambda d: captured.append(d))

        hook_handler = hooks["PreToolUse"][0]["hooks"][0]

        hook_input = {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript",
            "cwd": "/tmp/work",
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__orchestrator__ReviewDecision",
            "tool_input": {
                "decision": "ESCALATE",
                "summary": "Cannot determine correct behavior",
                "reason": "Requirements are ambiguous",
            },
        }

        result = await hook_handler(hook_input, None, {"signal": None})

        assert len(captured) == 1
        decision_data = captured[0]
        assert decision_data.decision == "ESCALATE"
        assert decision_data.reason == "Requirements are ambiguous"

    @pytest.mark.asyncio
    async def test_hook_returns_allow_decision(self):
        """Hook output allows tool execution to succeed."""
        hooks = create_review_decision_hook(lambda d: None)
        hook_handler = hooks["PreToolUse"][0]["hooks"][0]

        hook_input = {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript",
            "cwd": "/tmp/work",
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__orchestrator__ReviewDecision",
            "tool_input": {
                "decision": "APPROVE",
                "summary": "All good",
            },
        }

        result = await hook_handler(hook_input, None, {"signal": None})

        # Should allow the tool call (not block like question hook)
        assert result["decision"] == "allow"


class TestRunPhaseWithReviewDecisionCallback:
    """Tests for run_phase with review_decision_callback."""

    @pytest.mark.asyncio
    async def test_run_phase_with_callback_configures_hook(self, project_dir, tmp_path):
        """When callback provided, options include ReviewDecision hook."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        from orchestrator.agent import ResultMessage

        mock_result = MagicMock(spec=ResultMessage)
        mock_result.result = "Success"
        mock_result.is_error = False
        mock_result.session_id = None

        MockClient = create_mock_claude_sdk_client(messages=[mock_result])
        with patch("orchestrator.agent.ClaudeSDKClient", MockClient):
            # Provide a review_decision callback
            captured = []
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.REVIEW,
                worktree_path=worktree_path,
                review_decision_callback=lambda d: captured.append(d),
            )

            # Verify ClaudeSDKClient was called with options containing hooks
            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            assert options.hooks is not None
            assert "PreToolUse" in options.hooks

            # Find the ReviewDecision matcher (it's a regex pattern)
            # Chunk: docs/chunks/orch_reviewer_decision_mcp - Updated to MCP tool naming
            matchers = options.hooks["PreToolUse"]
            has_review_hook = any(
                hasattr(h["matcher"], "pattern") and h["matcher"].pattern == "^mcp__orchestrator__ReviewDecision$"
                for h in matchers
            )
            assert has_review_hook

    @pytest.mark.asyncio
    async def test_run_phase_captures_review_decision(self, project_dir, tmp_path):
        """When ReviewDecision intercepted, result has review_decision set."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        captured_decisions = []

        # Create a custom mock that simulates the SDK calling our hook
        class HookSimulatingMock(MockClaudeSDKClient):
            async def receive_response(self):
                # Yield the init message first
                yield {"type": "init", "session_id": "test-session-123"}

                # Simulate the SDK calling our hook when ReviewDecision is used
                if self.options and self.options.hooks and "PreToolUse" in self.options.hooks:
                    for matcher in self.options.hooks["PreToolUse"]:
                        if hasattr(matcher["matcher"], "pattern"):
                            hook_handler = matcher["hooks"][0]
                            hook_input = {
                                "session_id": "test-session-123",
                                "transcript_path": "/tmp/transcript",
                                "cwd": str(worktree_path),
                                "hook_event_name": "PreToolUse",
                                "tool_name": "mcp__orchestrator__ReviewDecision",
                                "tool_input": {
                                    "decision": "APPROVE",
                                    "summary": "All tests pass",
                                },
                            }
                            await hook_handler(hook_input, None, {"signal": None})

                # Simulate completion
                from orchestrator.agent import ResultMessage
                mock_result = MagicMock(spec=ResultMessage)
                mock_result.result = "Review complete"
                mock_result.is_error = False
                mock_result.session_id = None
                yield mock_result

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", HookSimulatingMock):
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.REVIEW,
                worktree_path=worktree_path,
                review_decision_callback=lambda d: captured_decisions.append(d),
            )

            # Verify result has review_decision
            assert result.completed is True
            assert result.review_decision is not None
            assert result.review_decision.decision == "APPROVE"
            assert result.review_decision.summary == "All tests pass"

            # Verify callback was called
            assert len(captured_decisions) == 1

    @pytest.mark.asyncio
    async def test_run_phase_captures_review_decision_from_message_stream(
        self, project_dir, tmp_path
    ):
        """ReviewDecision is captured from AssistantMessage content when hook doesn't fire.

        This tests the fallback behavior for MCP tools where PreToolUse hooks don't fire.
        The decision is captured directly from the ToolUseBlock in the message stream.
        """
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        captured_decisions = []

        # Create mock that yields AssistantMessage with ToolUseBlock but does NOT call hooks
        class MessageStreamCaptureMock(MockClaudeSDKClient):
            async def receive_response(self):
                # Yield init message
                yield {"type": "init", "session_id": "test-session-456"}

                # Yield AssistantMessage with ReviewDecision ToolUseBlock
                # This simulates what the real SDK sends when an MCP tool is called
                from orchestrator.agent import AssistantMessage

                tool_use_block = MagicMock()
                tool_use_block.name = "mcp__orchestrator__ReviewDecision"
                tool_use_block.input = {
                    "decision": "FEEDBACK",
                    "summary": "Missing test coverage",
                    "issues": [{"location": "src/main.py", "concern": "No tests"}],
                }

                assistant_msg = MagicMock(spec=AssistantMessage)
                assistant_msg.content = [tool_use_block]
                assistant_msg.session_id = None
                yield assistant_msg

                # Simulate completion
                from orchestrator.agent import ResultMessage

                mock_result = MagicMock(spec=ResultMessage)
                mock_result.result = "Review complete"
                mock_result.is_error = False
                mock_result.session_id = None
                yield mock_result

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MessageStreamCaptureMock):
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.REVIEW,
                worktree_path=worktree_path,
                review_decision_callback=lambda d: captured_decisions.append(d),
            )

            # Verify result has review_decision captured from message stream
            assert result.completed is True
            assert result.review_decision is not None
            assert result.review_decision.decision == "FEEDBACK"
            assert result.review_decision.summary == "Missing test coverage"
            assert result.review_decision.issues is not None
            assert len(result.review_decision.issues) == 1

            # Verify callback was called
            assert len(captured_decisions) == 1
            assert captured_decisions[0].decision == "FEEDBACK"

    @pytest.mark.asyncio
    async def test_run_phase_merges_all_hooks(self, project_dir, tmp_path):
        """run_phase merges sandbox, question, and review decision hooks."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        from orchestrator.agent import ResultMessage

        mock_result = MagicMock(spec=ResultMessage)
        mock_result.result = "Success"
        mock_result.is_error = False
        mock_result.session_id = None

        MockClient = create_mock_claude_sdk_client(messages=[mock_result])
        with patch("orchestrator.agent.ClaudeSDKClient", MockClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.REVIEW,
                worktree_path=worktree_path,
                question_callback=lambda q: None,
                review_decision_callback=lambda d: None,
            )

            # Verify ClaudeSDKClient was called with options containing all hooks
            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            assert options.hooks is not None
            assert "PreToolUse" in options.hooks

            matchers = options.hooks["PreToolUse"]
            matcher_types = []
            for m in matchers:
                if hasattr(m["matcher"], "pattern"):
                    matcher_types.append(m["matcher"].pattern)
                else:
                    matcher_types.append(m["matcher"])

            # Should have Bash (sandbox), AskUserQuestion (question), and ReviewDecision
            # Chunk: docs/chunks/orch_reviewer_decision_mcp - Updated to MCP tool naming
            assert "Bash" in matcher_types
            assert "AskUserQuestion" in matcher_types
            assert "^mcp__orchestrator__ReviewDecision$" in matcher_types


# Chunk: docs/chunks/orch_reviewer_decision_mcp - Tests for MCP server configuration
class TestMCPServerConfiguration:
    """Tests for MCP server configuration during REVIEW phase."""

    def test_create_orchestrator_mcp_server(self):
        """create_orchestrator_mcp_server returns valid MCP server config."""
        server_config = create_orchestrator_mcp_server()

        # Should return a dict with 'type': 'sdk'
        assert isinstance(server_config, dict)
        assert server_config.get("type") == "sdk"
        assert server_config.get("name") == "orchestrator"
        assert "instance" in server_config

    def test_review_decision_tool_is_decorated(self):
        """review_decision_tool is a decorated SdkMcpTool."""
        from claude_agent_sdk import SdkMcpTool

        # The @tool decorator creates an SdkMcpTool
        assert isinstance(review_decision_tool, SdkMcpTool)
        assert review_decision_tool.name == "ReviewDecision"
        assert "decision" in review_decision_tool.input_schema["required"]
        assert "summary" in review_decision_tool.input_schema["required"]

    @pytest.mark.asyncio
    async def test_run_phase_review_configures_mcp_server(self, project_dir, tmp_path):
        """REVIEW phase includes MCP server for ReviewDecision tool."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        from orchestrator.agent import ResultMessage

        mock_result = MagicMock(spec=ResultMessage)
        mock_result.result = "Success"
        mock_result.is_error = False
        mock_result.session_id = None

        MockClient = create_mock_claude_sdk_client(messages=[mock_result])
        with patch("orchestrator.agent.ClaudeSDKClient", MockClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.REVIEW,
                worktree_path=worktree_path,
                review_decision_callback=lambda d: None,
            )

            # Verify ClaudeSDKClient was called with mcp_servers containing orchestrator
            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            assert options.mcp_servers is not None
            assert "orchestrator" in options.mcp_servers
            # Should also allow the MCP tool
            assert "mcp__orchestrator__ReviewDecision" in options.allowed_tools

    @pytest.mark.asyncio
    async def test_run_phase_non_review_no_mcp_server(self, project_dir, tmp_path):
        """Non-REVIEW phases do not include MCP server."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        from orchestrator.agent import ResultMessage

        mock_result = MagicMock(spec=ResultMessage)
        mock_result.result = "Success"
        mock_result.is_error = False
        mock_result.session_id = None

        MockClient = create_mock_claude_sdk_client(messages=[mock_result])
        with patch("orchestrator.agent.ClaudeSDKClient", MockClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,  # Not REVIEW
                worktree_path=worktree_path,
            )

            # Verify ClaudeSDKClient was called without mcp_servers
            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            # mcp_servers should be empty or not set
            assert not options.mcp_servers or "orchestrator" not in options.mcp_servers
