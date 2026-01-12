# Chunk: docs/chunks/orch_scheduling - Agent runner tests
# Chunk: docs/chunks/orch_question_forward - Question intercept hook tests
"""Tests for the orchestrator agent runner."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.agent import (
    AgentRunner,
    AgentRunnerError,
    PHASE_SKILL_FILES,
    create_log_callback,
    create_question_intercept_hook,
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


# Chunk: docs/chunks/orch_question_forward - Question intercept hook tests
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


class TestRunPhaseWithQuestionCallback:
    """Tests for run_phase with question callback."""

    @pytest.mark.asyncio
    async def test_run_phase_with_callback_configures_hook(self, project_dir, tmp_path):
        """When callback provided, options include PreToolUse hook."""
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

            # Provide a question callback
            captured = []
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                question_callback=lambda q: captured.append(q),
            )

            # Verify query was called with options containing hooks
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args.kwargs
            options = call_kwargs["options"]
            assert options.hooks is not None
            assert "PreToolUse" in options.hooks

    @pytest.mark.asyncio
    async def test_run_phase_without_callback_no_hook(self, project_dir, tmp_path):
        """When no callback, options don't include hook."""
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

            # No question callback
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
            )

            # Verify query was called with options without hooks
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args.kwargs
            options = call_kwargs["options"]
            assert options.hooks is None

    @pytest.mark.asyncio
    async def test_run_phase_captures_question_on_intercept(self, project_dir, tmp_path):
        """When AskUserQuestion intercepted, result has suspended=True and question.

        This test directly tests the question_callback behavior by manually
        simulating what happens when the hook is triggered.
        """
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # We need to patch query in a way that:
        # 1. Captures the options passed to query (which includes our hook)
        # 2. Simulates the hook being called by the SDK
        # 3. Returns appropriate messages

        saved_options = None
        captured_questions = []

        with patch("orchestrator.agent.query") as mock_query:
            async def mock_async_iter(prompt, options):
                nonlocal saved_options
                saved_options = options

                # Simulate receiving an init message with session_id
                yield {"type": "init", "session_id": "test-session-123"}

                # Now, simulate the SDK calling our hook when AskUserQuestion is used
                # In the real SDK, this would happen automatically
                if options.hooks and "PreToolUse" in options.hooks:
                    for matcher in options.hooks["PreToolUse"]:
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

            mock_query.side_effect = mock_async_iter

            # Run with question callback
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                question_callback=lambda q: captured_questions.append(q),
            )

            # Verify the hook was configured
            assert saved_options is not None
            assert saved_options.hooks is not None
            assert "PreToolUse" in saved_options.hooks

            # Verify result is suspended with question data
            assert result.suspended is True
            assert result.completed is False
            assert result.question is not None
            assert result.question["question"] == "Which approach?"
            assert result.session_id == "test-session-123"

            # Verify callback was called
            assert len(captured_questions) == 1
            assert captured_questions[0]["question"] == "Which approach?"
