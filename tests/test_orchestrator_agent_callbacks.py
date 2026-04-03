# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_reviewer_decision_mcp - Updated tests for ClaudeSDKClient migration
"""Tests for the orchestrator agent runner callbacks and hooks."""

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


# Chunk: docs/chunks/orch_question_forward - Unit tests for run_phase with question callback
class TestRunPhaseWithQuestionCallback:
    """Tests for run_phase with question callback."""

    @pytest.mark.asyncio
    async def test_run_phase_with_callback_configures_hook(self, project_dir, tmp_path):
        """When callback provided, options include PreToolUse hook."""
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
            # Provide a question callback
            captured = []
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                question_callback=lambda q: captured.append(q),
            )

            # Verify ClaudeSDKClient was called with options containing hooks
            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            assert options.hooks is not None
            assert "PreToolUse" in options.hooks

    @pytest.mark.asyncio
    async def test_run_phase_without_callback_has_sandbox_hook_only(self, project_dir, tmp_path):
        """When no question callback, options include only sandbox hook."""
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
            # No question callback
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
            )

            # Verify ClaudeSDKClient was called with options containing only sandbox hook
            assert MockClaudeSDKClient.last_instance is not None
            options = MockClaudeSDKClient.last_instance.options
            # Sandbox hook should always be present
            assert options.hooks is not None
            assert "PreToolUse" in options.hooks
            matchers = [h["matcher"] for h in options.hooks["PreToolUse"]]
            # Only Bash (sandbox) hook, no AskUserQuestion hook
            assert "Bash" in matchers
            assert "AskUserQuestion" not in matchers

    @pytest.mark.asyncio
    async def test_run_phase_captures_question_on_intercept(self, project_dir, tmp_path):
        """When AskUserQuestion intercepted, result has suspended=True and question.

        This test directly tests the question_callback behavior by manually
        simulating what happens when the hook is triggered.
        """
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        captured_questions = []

        # Create a custom mock that simulates the SDK calling our hook
        class HookSimulatingMock(MockClaudeSDKClient):
            def __init__(self, options=None):
                super().__init__(options)
                self._messages = [{"type": "init", "session_id": "test-session-123"}]

            async def receive_response(self):
                # Yield the init message first
                yield {"type": "init", "session_id": "test-session-123"}

                # Simulate the SDK calling our hook when AskUserQuestion is used
                if self.options and self.options.hooks and "PreToolUse" in self.options.hooks:
                    for matcher in self.options.hooks["PreToolUse"]:
                        if matcher["matcher"] == "AskUserQuestion":
                            hook_handler = matcher["hooks"][0]
                            hook_input = {
                                "session_id": "test-session-123",
                                "transcript_path": "/tmp/transcript",
                                "cwd": str(worktree_path),
                                "hook_event_name": "PreToolUse",
                                "tool_name": "AskUserQuestion",
                                "tool_input": {
                                    "questions": [
                                        {
                                            "question": "Which approach?",
                                            "options": [{"label": "A"}, {"label": "B"}],
                                            "header": "Approach",
                                            "multiSelect": False,
                                        }
                                    ]
                                },
                            }
                            # Call the hook - this triggers our callback
                            await hook_handler(hook_input, None, {"signal": None})

                # Don't yield any more messages - the hook stopped the loop

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", HookSimulatingMock):
            # Run with question callback
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                question_callback=lambda q: captured_questions.append(q),
            )

            # Verify the hook was configured
            assert MockClaudeSDKClient.last_instance is not None
            assert MockClaudeSDKClient.last_instance.options.hooks is not None
            assert "PreToolUse" in MockClaudeSDKClient.last_instance.options.hooks

            # Verify result is suspended with question data
            assert result.suspended is True
            assert result.completed is False
            assert result.question is not None
            assert result.question["question"] == "Which approach?"
            assert result.session_id == "test-session-123"

            # Verify callback was called
            assert len(captured_questions) == 1
            assert captured_questions[0]["question"] == "Which approach?"


# Chunk: docs/chunks/orch_sandbox_enforcement - Unit tests for sandbox violation detection
class TestSandboxViolationDetection:
    """Tests for _is_sandbox_violation helper function."""

    def test_blocks_cd_to_host_repo(self):
        """Detects cd to host repository path as violation."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "cd /home/user/project", host, worktree
        )
        assert is_violation is True
        assert "host repository" in reason

    def test_blocks_cd_to_host_repo_with_single_quotes(self):
        """Detects cd with single-quoted path as violation."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "cd '/home/user/project'", host, worktree
        )
        assert is_violation is True

    def test_blocks_cd_to_host_repo_with_double_quotes(self):
        """Detects cd with double-quoted path as violation."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            'cd "/home/user/project"', host, worktree
        )
        assert is_violation is True

    def test_blocks_cd_to_host_repo_with_trailing_slash(self):
        """Detects cd to host repo with trailing slash as violation."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "cd /home/user/project/", host, worktree
        )
        assert is_violation is True

    def test_blocks_git_c_flag_to_host_repo(self):
        """Detects git -C targeting host repository as violation."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "git -C /home/user/project commit -m 'test'", host, worktree
        )
        assert is_violation is True
        assert "git -C" in reason

    def test_blocks_git_command_with_host_path(self):
        """Detects git commands referencing host repo path."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "git --git-dir=/home/user/project/.git status", host, worktree
        )
        assert is_violation is True
        assert "git command" in reason

    def test_blocks_cd_to_absolute_path_outside_worktree(self):
        """Detects cd to absolute path outside worktree as violation."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "cd /home/user/other", host, worktree
        )
        assert is_violation is True
        assert "outside worktree" in reason

    def test_allows_commands_within_worktree(self):
        """Normal commands in worktree are allowed."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "ls -la && cat README.md", host, worktree
        )
        assert is_violation is False
        assert reason is None

    def test_allows_relative_cd(self):
        """cd with relative paths is allowed."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "cd docs/chunks && ls", host, worktree
        )
        assert is_violation is False
        assert reason is None

    def test_allows_cd_within_worktree(self):
        """cd to absolute path within worktree is allowed."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "cd /home/user/project/.ve/chunks/test/worktree/src", host, worktree
        )
        assert is_violation is False
        assert reason is None

    def test_allows_cd_to_tmp(self):
        """cd to /tmp is allowed (safe system path)."""
        host = Path("/home/user/project")
        worktree = Path("/home/user/project/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "cd /tmp && ls", host, worktree
        )
        assert is_violation is False
        assert reason is None

    def test_dynamic_path_detection(self):
        """Paths are dynamically checked, not hardcoded."""
        # Test with different host/worktree paths
        host1 = Path("/foo/bar")
        worktree1 = Path("/foo/bar/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "cd /foo/bar", host1, worktree1
        )
        assert is_violation is True

        # Same command with different paths should not match
        host2 = Path("/different/path")
        worktree2 = Path("/different/path/.ve/chunks/test/worktree")

        is_violation, reason = _is_sandbox_violation(
            "cd /foo/bar", host2, worktree2
        )
        # This should still be blocked as it's outside worktree2
        assert is_violation is True
        assert "outside worktree" in reason


# Chunk: docs/chunks/orch_sandbox_enforcement - Unit tests for hook merging
class TestMergeHooks:
    """Tests for _merge_hooks helper function."""

    def test_merges_single_hook_config(self):
        """Single hook config is returned unchanged."""
        config = {"PreToolUse": [{"matcher": "Bash", "hooks": [], "timeout": None}]}
        merged = _merge_hooks(config)
        assert merged == config

    def test_merges_multiple_hook_configs(self):
        """Multiple configs are merged into one."""
        config1 = {"PreToolUse": [{"matcher": "Bash", "hooks": [], "timeout": None}]}
        config2 = {"PreToolUse": [{"matcher": "AskUserQuestion", "hooks": [], "timeout": None}]}

        merged = _merge_hooks(config1, config2)

        assert "PreToolUse" in merged
        assert len(merged["PreToolUse"]) == 2
        matchers = [h["matcher"] for h in merged["PreToolUse"]]
        assert "Bash" in matchers
        assert "AskUserQuestion" in matchers

    def test_merges_different_event_types(self):
        """Different event types are kept separate."""
        config1 = {"PreToolUse": [{"matcher": "Bash", "hooks": [], "timeout": None}]}
        config2 = {"PostToolUse": [{"matcher": "Bash", "hooks": [], "timeout": None}]}

        merged = _merge_hooks(config1, config2)

        assert "PreToolUse" in merged
        assert "PostToolUse" in merged
