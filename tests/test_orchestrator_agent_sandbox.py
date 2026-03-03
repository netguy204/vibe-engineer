# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_reviewer_decision_mcp - Updated tests for ClaudeSDKClient migration
"""Tests for the orchestrator agent sandbox enforcement."""

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
    # Create .claude/commands directory
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Create skill files with minimal content
    skill_content = """---
description: Test skill
---

## Instructions

This is a test skill for {phase}.
"""
    for phase, filename in PHASE_SKILL_FILES.items():
        (commands_dir / filename).write_text(
            skill_content.format(phase=phase.value)
        )

    return tmp_path


# Chunk: docs/chunks/orch_sandbox_enforcement - Unit tests for sandbox enforcement hook
class TestSandboxEnforcementHook:
    """Tests for sandbox enforcement hook creation."""

    def test_creates_valid_hook_config(self):
        """Hook config has correct structure for PreToolUse."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        hooks = create_sandbox_enforcement_hook(host, worktree)

        assert "PreToolUse" in hooks
        assert len(hooks["PreToolUse"]) == 1
        hook_matcher = hooks["PreToolUse"][0]
        assert hook_matcher["matcher"] == "Bash"
        assert hook_matcher["hooks"] is not None
        assert len(hook_matcher["hooks"]) == 1

    @pytest.mark.asyncio
    async def test_hook_blocks_violation(self):
        """Hook returns block decision for violations."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        hooks = create_sandbox_enforcement_hook(host, worktree)
        hook_handler = hooks["PreToolUse"][0]["hooks"][0]

        hook_input = {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript",
            "cwd": str(worktree),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "cd /home/user/project && git commit -m 'test'"},
        }

        result = await hook_handler(hook_input, None, {"signal": None})

        assert result["decision"] == "block"
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_hook_allows_safe_commands(self):
        """Hook returns allow decision for safe commands."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        hooks = create_sandbox_enforcement_hook(host, worktree)
        hook_handler = hooks["PreToolUse"][0]["hooks"][0]

        hook_input = {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript",
            "cwd": str(worktree),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "git status && ls docs/"},
        }

        result = await hook_handler(hook_input, None, {"signal": None})

        assert result["decision"] == "allow"


# Chunk: docs/chunks/orch_sandbox_enforcement - Integration tests for AgentRunner sandbox
class TestAgentRunnerSandboxIntegration:
    """Tests for sandbox integration in AgentRunner."""

    def test_agent_runner_stores_host_repo_path(self, project_dir):
        """AgentRunner stores host_repo_path from project_dir."""
        runner = AgentRunner(project_dir)
        assert runner.host_repo_path == project_dir.resolve()

    @pytest.mark.asyncio
    async def test_run_phase_always_configures_sandbox_hook(self, project_dir, tmp_path):
        """run_phase includes sandbox hook even without question_callback."""
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
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
            )

            # Verify ClaudeSDKClient was called with options containing hooks
            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            assert options.hooks is not None
            assert "PreToolUse" in options.hooks
            # Should have Bash matcher for sandbox enforcement
            matchers = [h["matcher"] for h in options.hooks["PreToolUse"]]
            assert "Bash" in matchers

    @pytest.mark.asyncio
    async def test_run_phase_merges_sandbox_and_question_hooks(self, project_dir, tmp_path):
        """run_phase merges sandbox hook with question hook when callback provided."""
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
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                question_callback=lambda q: None,
            )

            # Verify ClaudeSDKClient was called with options containing both hooks
            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            assert options.hooks is not None
            assert "PreToolUse" in options.hooks
            matchers = [h["matcher"] for h in options.hooks["PreToolUse"]]
            # Should have both Bash (sandbox) and AskUserQuestion (question)
            assert "Bash" in matchers
            assert "AskUserQuestion" in matchers

    @pytest.mark.asyncio
    async def test_run_phase_sets_git_environment(self, project_dir, tmp_path):
        """run_phase sets GIT_DIR and GIT_WORK_TREE environment variables."""
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
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
            )

            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            assert options.env is not None
            assert options.env["GIT_DIR"] == str(worktree_path / ".git")
            assert options.env["GIT_WORK_TREE"] == str(worktree_path)

    @pytest.mark.asyncio
    async def test_run_phase_includes_sandbox_rules_in_prompt(self, project_dir, tmp_path):
        """run_phase prepends sandbox rules to the prompt."""
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
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
            )

            assert MockClaudeSDKClient.last_instance is not None
            prompt = MockClaudeSDKClient.last_instance._query_prompt
            assert "SANDBOX RULES" in prompt
            assert "isolated git worktree" in prompt
            assert "NEVER use `cd` with absolute paths" in prompt

    # Chunk: docs/chunks/orch_reviewer_decision_mcp - Removed run_commit test
    # run_commit() method was removed as deprecated

    @pytest.mark.asyncio
    async def test_resume_for_active_status_configures_sandbox_hook(self, project_dir, tmp_path):
        """resume_for_active_status includes sandbox hook."""
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
            await runner.resume_for_active_status(
                chunk="test_chunk",
                worktree_path=worktree_path,
                session_id="test-session-id",
            )

            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            assert options.hooks is not None
            assert "PreToolUse" in options.hooks
            matchers = [h["matcher"] for h in options.hooks["PreToolUse"]]
            assert "Bash" in matchers
