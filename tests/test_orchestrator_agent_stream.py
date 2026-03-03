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


# Chunk: docs/chunks/orch_question_capture - Tests for AskUserQuestion capture from message stream
class TestAskUserQuestionMessageStreamCapture:
    """Tests for capturing AskUserQuestion from AssistantMessage content.

    PreToolUse hooks don't fire for built-in tools like AskUserQuestion.
    This tests the fallback behavior where the question is captured directly
    from the ToolUseBlock in the message stream.
    """

    @pytest.mark.asyncio
    async def test_captures_question_from_assistant_message(self, project_dir, tmp_path):
        """AskUserQuestion is captured from AssistantMessage when hook doesn't fire.

        This tests the behavior for built-in tools where PreToolUse hooks don't fire.
        The question is captured directly from the ToolUseBlock in the message stream.
        """
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        captured_questions = []

        # Create mock that yields AssistantMessage with ToolUseBlock but does NOT call hooks
        class MessageStreamCaptureMock(MockClaudeSDKClient):
            async def receive_response(self):
                # Yield init message
                yield {"type": "init", "session_id": "test-session-789"}

                # Yield AssistantMessage with AskUserQuestion ToolUseBlock
                # This simulates what the real SDK sends when a built-in tool is called
                from orchestrator.agent import AssistantMessage

                tool_use_block = MagicMock()
                tool_use_block.name = "AskUserQuestion"
                tool_use_block.input = {
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
                }

                assistant_msg = MagicMock(spec=AssistantMessage)
                assistant_msg.content = [tool_use_block]
                assistant_msg.session_id = None
                yield assistant_msg

                # Don't yield ResultMessage - the agent should suspend on question capture

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MessageStreamCaptureMock):
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                question_callback=lambda q: captured_questions.append(q),
            )

            # Verify result is suspended with question captured from message stream
            assert result.suspended is True
            assert result.completed is False
            assert result.question is not None
            assert result.question["question"] == "Which database should we use?"
            assert len(result.question["options"]) == 2
            assert result.question["header"] == "Database"
            assert result.question["multiSelect"] is False
            assert result.session_id == "test-session-789"

            # Verify callback was called
            assert len(captured_questions) == 1
            assert captured_questions[0]["question"] == "Which database should we use?"

    @pytest.mark.asyncio
    async def test_captures_question_with_empty_questions_array(self, project_dir, tmp_path):
        """Handles malformed AskUserQuestion input gracefully."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        captured_questions = []

        class MessageStreamCaptureMock(MockClaudeSDKClient):
            async def receive_response(self):
                yield {"type": "init", "session_id": "test-session-fallback"}

                from orchestrator.agent import AssistantMessage

                tool_use_block = MagicMock()
                tool_use_block.name = "AskUserQuestion"
                tool_use_block.input = {"questions": []}  # Empty questions array

                assistant_msg = MagicMock(spec=AssistantMessage)
                assistant_msg.content = [tool_use_block]
                assistant_msg.session_id = None
                yield assistant_msg

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MessageStreamCaptureMock):
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                question_callback=lambda q: captured_questions.append(q),
            )

            # Should still suspend with fallback question data
            assert result.suspended is True
            assert result.question is not None
            assert "Agent asked a question" in result.question["question"]
            assert len(captured_questions) == 1

    @pytest.mark.asyncio
    async def test_only_captures_first_question_call(self, project_dir, tmp_path):
        """Only the first AskUserQuestion call is captured."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        captured_questions = []

        class MessageStreamCaptureMock(MockClaudeSDKClient):
            async def receive_response(self):
                yield {"type": "init", "session_id": "test-session-multi"}

                from orchestrator.agent import AssistantMessage

                # First tool call
                tool_use_block1 = MagicMock()
                tool_use_block1.name = "AskUserQuestion"
                tool_use_block1.input = {
                    "questions": [{"question": "First question?", "options": []}]
                }

                # Second tool call in same message
                tool_use_block2 = MagicMock()
                tool_use_block2.name = "AskUserQuestion"
                tool_use_block2.input = {
                    "questions": [{"question": "Second question?", "options": []}]
                }

                assistant_msg = MagicMock(spec=AssistantMessage)
                assistant_msg.content = [tool_use_block1, tool_use_block2]
                assistant_msg.session_id = None
                yield assistant_msg

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MessageStreamCaptureMock):
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                question_callback=lambda q: captured_questions.append(q),
            )

            # Only first question should be captured
            assert result.question is not None
            assert result.question["question"] == "First question?"
            assert len(captured_questions) == 1
            assert captured_questions[0]["question"] == "First question?"

    @pytest.mark.asyncio
    async def test_captures_all_questions_in_tool_input(self, project_dir, tmp_path):
        """All questions from a single AskUserQuestion call are preserved."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        captured_questions = []

        class MessageStreamCaptureMock(MockClaudeSDKClient):
            async def receive_response(self):
                yield {"type": "init", "session_id": "test-session-all-questions"}

                from orchestrator.agent import AssistantMessage

                tool_use_block = MagicMock()
                tool_use_block.name = "AskUserQuestion"
                tool_use_block.input = {
                    "questions": [
                        {"question": "Question 1?", "options": [], "header": "Q1"},
                        {"question": "Question 2?", "options": [], "header": "Q2"},
                        {"question": "Question 3?", "options": [], "header": "Q3"},
                    ]
                }

                assistant_msg = MagicMock(spec=AssistantMessage)
                assistant_msg.content = [tool_use_block]
                assistant_msg.session_id = None
                yield assistant_msg

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MessageStreamCaptureMock):
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                question_callback=lambda q: captured_questions.append(q),
            )

            # First question should be primary
            assert result.question["question"] == "Question 1?"
            # All questions should be preserved in all_questions
            assert len(result.question["all_questions"]) == 3
            assert result.question["all_questions"][0]["question"] == "Question 1?"
            assert result.question["all_questions"][1]["question"] == "Question 2?"
            assert result.question["all_questions"][2]["question"] == "Question 3?"

    @pytest.mark.asyncio
    async def test_no_callback_still_captures_question(self, project_dir, tmp_path):
        """Question is captured even without callback, result is suspended."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        class MessageStreamCaptureMock(MockClaudeSDKClient):
            async def receive_response(self):
                yield {"type": "init", "session_id": "test-session-no-callback"}

                from orchestrator.agent import AssistantMessage

                tool_use_block = MagicMock()
                tool_use_block.name = "AskUserQuestion"
                tool_use_block.input = {
                    "questions": [{"question": "No callback question?", "options": []}]
                }

                assistant_msg = MagicMock(spec=AssistantMessage)
                assistant_msg.content = [tool_use_block]
                assistant_msg.session_id = None
                yield assistant_msg

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MessageStreamCaptureMock):
            # Run WITHOUT question_callback
            result = await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                # No question_callback provided
            )

            # Should still suspend with question captured
            assert result.suspended is True
            assert result.question is not None
            assert result.question["question"] == "No callback question?"
