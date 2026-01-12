# Chunk: docs/chunks/orch_scheduling - Agent runner tests
"""Tests for the orchestrator agent runner."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.agent import (
    AgentRunner,
    AgentRunnerError,
    PHASE_SKILL_FILES,
    create_log_callback,
    _load_skill_content,
    _is_error_result,
)
from orchestrator.models import AgentResult, WorkUnitPhase


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


class TestPhaseSkillFiles:
    """Tests for phase-to-skill-file mapping."""

    def test_all_phases_have_skill_files(self):
        """Every phase has a corresponding skill file."""
        for phase in WorkUnitPhase:
            assert phase in PHASE_SKILL_FILES

    def test_skill_file_format(self):
        """Skill files are .md files."""
        for filename in PHASE_SKILL_FILES.values():
            assert filename.endswith(".md")


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


class TestIsErrorResult:
    """Tests for error detection in result text."""

    def test_detects_unknown_slash_command(self):
        """Detects 'Unknown slash command' error."""
        assert _is_error_result("Unknown slash command: foo") is True

    def test_detects_error_prefix(self):
        """Detects 'Error:' prefix."""
        assert _is_error_result("Error: something went wrong") is True

    def test_detects_failed_to(self):
        """Detects 'Failed to' message."""
        assert _is_error_result("Failed to read file") is True

    def test_normal_result_not_error(self):
        """Normal result text is not an error."""
        assert _is_error_result("Task completed successfully") is False
        assert _is_error_result("Implementation done") is False


class TestAgentRunner:
    """Tests for AgentRunner class."""

    def test_get_skill_path(self, project_dir):
        """Returns correct path for each phase."""
        runner = AgentRunner(project_dir)

        for phase, filename in PHASE_SKILL_FILES.items():
            path = runner.get_skill_path(phase)
            assert path == project_dir / ".claude" / "commands" / filename

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
        commands_dir = project_dir / ".claude" / "commands"
        (commands_dir / "chunk-create.md").write_text("""---
description: Create chunk
---

The operator wants: $ARGUMENTS
""")

        runner = AgentRunner(project_dir)

        prompt = runner.get_phase_prompt("my_chunk", WorkUnitPhase.GOAL)

        assert "my_chunk" in prompt
        assert "$ARGUMENTS" not in prompt


class TestAgentRunnerPhaseExecution:
    """Tests for phase execution (mocked)."""

    @pytest.mark.asyncio
    async def test_run_phase_completed(self, project_dir, tmp_path):
        """Successful phase execution returns completed result."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Mock the query function to return a ResultMessage
        with patch("orchestrator.agent.query") as mock_query:
            from orchestrator.agent import ResultMessage

            mock_result = MagicMock(spec=ResultMessage)
            mock_result.result = "Success"
            mock_result.is_error = False

            async def mock_async_iter(*args, **kwargs):
                yield mock_result

            mock_query.return_value = mock_async_iter()

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

        # Mock the query function to raise an error
        with patch("orchestrator.agent.query") as mock_query:
            async def mock_async_iter(*args, **kwargs):
                raise Exception("Test error")
                yield  # Make it a generator

            mock_query.return_value = mock_async_iter()

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
    async def test_run_phase_error_from_result(self, project_dir, tmp_path):
        """Error in result text returns error result."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Mock the query function to return an error result
        with patch("orchestrator.agent.query") as mock_query:
            from orchestrator.agent import ResultMessage

            mock_result = MagicMock(spec=ResultMessage)
            mock_result.result = "Unknown slash command: foo"
            mock_result.is_error = False

            async def mock_async_iter(*args, **kwargs):
                yield mock_result

            mock_query.return_value = mock_async_iter()

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

        with patch("orchestrator.agent.query") as mock_query:
            from orchestrator.agent import ResultMessage

            mock_result = MagicMock(spec=ResultMessage)
            mock_result.result = "Success"
            mock_result.is_error = False

            async def mock_async_iter(*args, **kwargs):
                yield mock_result

            mock_query.return_value = mock_async_iter()

            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
            )

            # Verify query was called with options containing setting_sources
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args.kwargs
            options = call_kwargs["options"]
            assert options.setting_sources == ["project"]

    @pytest.mark.asyncio
    async def test_run_commit_includes_setting_sources(self, project_dir, tmp_path):
        """run_commit passes setting_sources=['project'] to options."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create chunk-commit skill file
        commit_skill = project_dir / ".claude" / "commands" / "chunk-commit.md"
        commit_skill.write_text("---\ndescription: Commit\n---\n\nCommit changes.")

        with patch("orchestrator.agent.query") as mock_query:
            from orchestrator.agent import ResultMessage

            mock_result = MagicMock(spec=ResultMessage)
            mock_result.result = "Success"
            mock_result.is_error = False

            async def mock_async_iter(*args, **kwargs):
                yield mock_result

            mock_query.return_value = mock_async_iter()

            await runner.run_commit(
                chunk="test_chunk",
                worktree_path=worktree_path,
            )

            # Verify query was called with options containing setting_sources
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args.kwargs
            options = call_kwargs["options"]
            assert options.setting_sources == ["project"]

    @pytest.mark.asyncio
    async def test_resume_for_active_status_includes_setting_sources(
        self, project_dir, tmp_path
    ):
        """resume_for_active_status passes setting_sources=['project'] to options."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        with patch("orchestrator.agent.query") as mock_query:
            from orchestrator.agent import ResultMessage

            mock_result = MagicMock(spec=ResultMessage)
            mock_result.result = "Success"
            mock_result.is_error = False

            async def mock_async_iter(*args, **kwargs):
                yield mock_result

            mock_query.return_value = mock_async_iter()

            await runner.resume_for_active_status(
                chunk="test_chunk",
                worktree_path=worktree_path,
                session_id="test-session-id",
            )

            # Verify query was called with options containing setting_sources
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args.kwargs
            options = call_kwargs["options"]
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
