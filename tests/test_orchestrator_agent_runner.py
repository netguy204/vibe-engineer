# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_reviewer_decision_mcp - Updated tests for ClaudeSDKClient migration
"""Tests for the orchestrator agent runner."""

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


class TestAgentRunnerPhaseExecution:
    """Tests for phase execution (mocked)."""

    @pytest.mark.asyncio
    async def test_run_phase_completed(self, project_dir, tmp_path):
        """Successful phase execution returns completed result."""
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
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
            )

        assert isinstance(result, AgentResult)
        assert result.completed is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_phase_error_from_exception(self, project_dir, tmp_path):
        """Phase execution exception returns error result."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        MockClient = create_mock_claude_sdk_client(exception=Exception("Test error"))
        with patch("orchestrator.agent.ClaudeSDKClient", MockClient):
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
            )

        assert isinstance(result, AgentResult)
        assert result.completed is False
        assert result.error is not None
        assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_run_phase_error_from_sdk_flag(self, project_dir, tmp_path):
        """Error from SDK is_error=True flag returns error result."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        from orchestrator.agent import ResultMessage

        mock_result = MagicMock(spec=ResultMessage)
        mock_result.result = "Unknown slash command: foo"
        mock_result.is_error = True  # SDK indicates this is an error
        mock_result.session_id = None

        MockClient = create_mock_claude_sdk_client(messages=[mock_result])
        with patch("orchestrator.agent.ClaudeSDKClient", MockClient):
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
            )

        assert isinstance(result, AgentResult)
        assert result.completed is False
        assert result.error is not None
        assert "Unknown slash command" in result.error


class TestSettingSourcesConfiguration:
    """Tests for setting_sources configuration in ClaudeAgentOptions.

    Verifies that all methods that create ClaudeAgentOptions include
    setting_sources=["project"] to enable project-level skills/commands.
    """

    @pytest.mark.asyncio
    async def test_run_phase_includes_setting_sources(self, project_dir, tmp_path):
        """run_phase passes setting_sources=['project'] to options."""
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

            # Verify ClaudeSDKClient was called with options containing setting_sources
            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            assert options.setting_sources == ["project"]

    # Chunk: docs/chunks/orch_reviewer_decision_mcp - Removed run_commit test
    # run_commit() method was removed as deprecated

    @pytest.mark.asyncio
    async def test_resume_for_active_status_includes_setting_sources(
        self, project_dir, tmp_path
    ):
        """resume_for_active_status passes setting_sources=['project'] to options."""
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

            # Verify ClaudeSDKClient was called with options containing setting_sources
            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            assert options.setting_sources == ["project"]


class TestLogCallback:
    """Tests for log callback creation."""

    def test_create_log_callback(self, tmp_path):
        """Creates callback that writes to file."""
        log_dir = tmp_path / "logs"

        callback = create_log_callback("test_chunk", WorkUnitPhase.PLAN, log_dir)

        # Call the callback
        callback("test message")

        # Check file was created
        log_file = log_dir / "plan.txt"
        assert log_file.exists()
        assert "test message" in log_file.read_text()

    def test_log_callback_appends(self, tmp_path):
        """Callback appends to existing log."""
        log_dir = tmp_path / "logs"

        callback = create_log_callback("test_chunk", WorkUnitPhase.PLAN, log_dir)

        callback("message 1")
        callback("message 2")

        log_file = log_dir / "plan.txt"
        content = log_file.read_text()
        assert "message 1" in content
        assert "message 2" in content

    def test_log_callback_creates_dir(self, tmp_path):
        """Callback creates log directory if needed."""
        log_dir = tmp_path / "nested" / "logs"

        callback = create_log_callback("test_chunk", WorkUnitPhase.IMPLEMENT, log_dir)
        callback("test")

        assert (log_dir / "implement.txt").exists()


# Chunk: docs/chunks/orch_question_forward - Unit tests for hook creation and question extraction
class TestQuestionInterceptHook:
    """Tests for AskUserQuestion interception hook."""

    def test_create_hook_returns_valid_hook_config(self):
        """Hook config has correct structure for PreToolUse."""
        captured = []
        hooks = create_question_intercept_hook(lambda q: captured.append(q))

        assert "PreToolUse" in hooks
        assert len(hooks["PreToolUse"]) == 1

        hook_matcher = hooks["PreToolUse"][0]
        assert hook_matcher["matcher"] == "AskUserQuestion"
        assert hook_matcher["hooks"] is not None
        assert len(hook_matcher["hooks"]) == 1

    @pytest.mark.asyncio
    async def test_hook_extracts_question_data(self):
        """Hook callback receives question text and options."""
        captured = []
        hooks = create_question_intercept_hook(lambda q: captured.append(q))

        # Get the hook handler
        hook_handler = hooks["PreToolUse"][0]["hooks"][0]

        # Simulate PreToolUseHookInput for AskUserQuestion
        hook_input = {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript",
            "cwd": "/tmp/work",
            "hook_event_name": "PreToolUse",
            "tool_name": "AskUserQuestion",
            "tool_input": {
                "questions": [
                    {
                        "question": "Which database should we use?",
                        "options": [
                            {"label": "PostgreSQL", "description": "Relational DB"},
                            {"label": "MongoDB", "description": "Document DB"},
                        ],
                        "header": "Database",
                        "multiSelect": False,
                    }
                ]
            },
        }

        # Call the hook
        from orchestrator.agent import HookContext

        result = await hook_handler(hook_input, None, {"signal": None})

        # Verify callback was called with extracted data
        assert len(captured) == 1
        question_data = captured[0]
        assert question_data["question"] == "Which database should we use?"
        assert len(question_data["options"]) == 2
        assert question_data["header"] == "Database"
        assert question_data["multiSelect"] is False
        assert len(question_data["all_questions"]) == 1

    @pytest.mark.asyncio
    async def test_hook_returns_block_decision(self):
        """Hook output blocks tool execution."""
        hooks = create_question_intercept_hook(lambda q: None)
        hook_handler = hooks["PreToolUse"][0]["hooks"][0]

        hook_input = {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript",
            "cwd": "/tmp/work",
            "hook_event_name": "PreToolUse",
            "tool_name": "AskUserQuestion",
            "tool_input": {"questions": [{"question": "Test?"}]},
        }

        result = await hook_handler(hook_input, None, {"signal": None})

        assert result["decision"] == "block"

    @pytest.mark.asyncio
    async def test_hook_sets_stop_reason(self):
        """Hook output sets stopReason to terminate loop."""
        hooks = create_question_intercept_hook(lambda q: None)
        hook_handler = hooks["PreToolUse"][0]["hooks"][0]

        hook_input = {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript",
            "cwd": "/tmp/work",
            "hook_event_name": "PreToolUse",
            "tool_name": "AskUserQuestion",
            "tool_input": {"questions": [{"question": "Test?"}]},
        }

        result = await hook_handler(hook_input, None, {"signal": None})

        assert result["stopReason"] == "question_queued"
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_hook_handles_empty_questions_array(self):
        """Hook handles malformed tool_input gracefully."""
        captured = []
        hooks = create_question_intercept_hook(lambda q: captured.append(q))
        hook_handler = hooks["PreToolUse"][0]["hooks"][0]

        hook_input = {
            "session_id": "test-session",
            "transcript_path": "/tmp/transcript",
            "cwd": "/tmp/work",
            "hook_event_name": "PreToolUse",
            "tool_name": "AskUserQuestion",
            "tool_input": {"questions": []},  # Empty questions
        }

        result = await hook_handler(hook_input, None, {"signal": None})

        assert len(captured) == 1
        # Should have fallback question data
        assert "Agent asked a question" in captured[0]["question"]
