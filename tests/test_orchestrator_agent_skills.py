# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_reviewer_decision_mcp - Updated tests for ClaudeSDKClient migration
"""Tests for the orchestrator agent runner - skill and utility tests."""

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


class TestPhaseSkillFiles:
    """Tests for phase-to-skill-file mapping."""

    def test_all_phases_have_skill_files(self):
        """Every phase has a corresponding skill file."""
        for phase in WorkUnitPhase:
            assert phase in PHASE_SKILL_FILES

    def test_skill_name_format(self):
        """Skill names are bare directory names (no extension)."""
        for skill_name in PHASE_SKILL_FILES.values():
            assert not skill_name.endswith(".md")
            assert "/" not in skill_name


class TestLoadSkillContent:
    """Tests for skill content loading."""

    def test_load_skill_content_strips_frontmatter(self, tmp_path):
        """Frontmatter is stripped from loaded content."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text("""---
description: Test
---

## Content

Actual content here.
""")

        content = _load_skill_content(skill_file)

        assert "description:" not in content
        assert "---" not in content
        assert "Actual content here." in content

    def test_load_skill_content_handles_no_frontmatter(self, tmp_path):
        """Content without frontmatter is returned as-is."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text("Just plain content")

        content = _load_skill_content(skill_file)

        assert content == "Just plain content"


class TestErrorDetectionRemoval:
    """Tests verifying heuristic error detection is removed.

    The SDK's `is_error` flag is authoritative for error detection.
    Text content should never trigger error interpretation when is_error=False.
    """

    @pytest.mark.asyncio
    async def test_verbose_success_with_failed_to_text_not_error(self, project_dir, tmp_path):
        """Success result containing 'Failed to' in text is still success.

        A ResultMessage with is_error=False but text containing "Failed to"
        should NOT be treated as an error. This prevents false positives when
        agents report on things that failed during successful completion.
        """
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        from orchestrator.agent import ResultMessage

        mock_result = MagicMock(spec=ResultMessage)
        # Verbose success with "Failed to" phrase - should still be success
        mock_result.result = (
            "Successfully completed the implementation. "
            "Note: Failed to find optional file X, proceeded without it."
        )
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
    async def test_verbose_success_with_error_colon_text_not_error(self, project_dir, tmp_path):
        """Success result containing 'Error:' in text is still success.

        A ResultMessage with is_error=False but text containing "Error:"
        should NOT be treated as an error. This prevents false positives when
        agents report error counts or mention errors they fixed.
        """
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        from orchestrator.agent import ResultMessage

        mock_result = MagicMock(spec=ResultMessage)
        # Verbose success with "Error:" phrase - should still be success
        mock_result.result = (
            "Implementation complete. Error: 0 found. "
            "All tests passing."
        )
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
    async def test_verbose_success_with_could_not_text_not_error(self, project_dir, tmp_path):
        """Success result containing 'Could not' in text is still success."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        from orchestrator.agent import ResultMessage

        mock_result = MagicMock(spec=ResultMessage)
        mock_result.result = (
            "Task completed. Could not find optional dependency, "
            "using fallback approach which worked fine."
        )
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
    async def test_actual_sdk_error_still_detected(self, project_dir, tmp_path):
        """ResultMessage with is_error=True is correctly treated as error.

        The SDK's is_error flag is authoritative - when it's True,
        we should report an error regardless of text content.
        """
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        from orchestrator.agent import ResultMessage

        mock_result = MagicMock(spec=ResultMessage)
        mock_result.result = "Something went wrong"
        mock_result.is_error = True  # SDK says it's an error
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


class TestAgentRunner:
    """Tests for AgentRunner class."""

    def test_get_skill_path(self, project_dir):
        """Returns correct path under .agents/skills/ for each phase."""
        runner = AgentRunner(project_dir)

        for phase, skill_name in PHASE_SKILL_FILES.items():
            path = runner.get_skill_path(phase)
            assert path == project_dir / ".agents" / "skills" / skill_name / "SKILL.md"

    def test_get_phase_prompt_loads_content(self, project_dir):
        """Phase prompt loads content from skill file."""
        runner = AgentRunner(project_dir)

        prompt = runner.get_phase_prompt("test_chunk", WorkUnitPhase.PLAN)

        # Should contain the skill content (frontmatter stripped)
        assert "Instructions" in prompt
        assert "---" not in prompt  # Frontmatter stripped

    def test_get_phase_prompt_goal_replaces_arguments(self, project_dir):
        """GOAL phase prompt replaces $ARGUMENTS placeholder."""
        # Create a skill file with $ARGUMENTS
        skills_dir = project_dir / ".agents" / "skills" / "chunk-create"
        skills_dir.mkdir(parents=True, exist_ok=True)
        (skills_dir / "SKILL.md").write_text("""---
description: Create chunk
---

The operator wants: $ARGUMENTS
""")

        runner = AgentRunner(project_dir)

        prompt = runner.get_phase_prompt("my_chunk", WorkUnitPhase.GOAL)

        assert "my_chunk" in prompt
        assert "$ARGUMENTS" not in prompt
