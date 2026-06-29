# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_seam - Unit tests for the AgentBackend seam
# Chunk: docs/chunks/backend_logparse - Tests for _emit_log_events and LogEvent types
"""Tests for the backend-agnostic AgentBackend seam.

These cover the contract types, that AgentRunner delegates to an injected
backend (proving the seam is real and swappable), and that _emit_log_events
correctly translates SDK message shapes into normalized LogEvents.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from orchestrator.agent import AgentRunner
from orchestrator.backend import (
    AgentBackend,
    LogEvent,
    ResultEvent,
    SessionRequest,
    TextEvent,
    ToolCallEvent,
    ToolDecision,
    ToolResultEvent,
    ToolUse,
    is_sandbox_violation,
)
from orchestrator.backends.claude import _emit_log_events
from orchestrator.models import AgentResult, WorkUnitPhase


@pytest.fixture
def project_dir(tmp_path):
    """A valid project directory. Phase prompts load from the repo `commands/`
    dir via get_skill_path, so this only needs to be a real directory."""
    proj = tmp_path / "project"
    proj.mkdir()
    return proj


class RecordingBackend:
    """Fake AgentBackend: records the request and returns a fixed result."""

    def __init__(self, result: AgentResult | None = None):
        self.result = result or AgentResult(
            completed=True, suspended=False, session_id="fake-sess"
        )
        self.request: SessionRequest | None = None

    async def run(self, request: SessionRequest) -> AgentResult:
        self.request = request
        return self.result


def test_tool_decision_values():
    assert ToolDecision.ALLOW == "allow"
    assert ToolDecision.DENY == "deny"


def test_tool_use_defaults():
    tu = ToolUse(tool_name="Bash", tool_input={"command": "ls"})
    assert tu.command is None
    assert tu.cwd is None


def test_session_request_defaults():
    req = SessionRequest(
        prompt="hi", cwd=Path("/wt"), host_repo_path=Path("/host"), env={}, max_turns=5
    )
    assert req.allowed_tools == []
    assert req.resume_session_id is None
    assert req.expose_review_tool is False
    assert req.on_question is None
    assert req.on_review_decision is None
    assert req.on_log is None


def test_recording_backend_satisfies_protocol():
    backend: AgentBackend = RecordingBackend()
    assert hasattr(backend, "run")


@pytest.mark.asyncio
async def test_run_phase_delegates_to_injected_backend(project_dir, tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    backend = RecordingBackend(
        AgentResult(completed=True, suspended=False, session_id="s1")
    )
    runner = AgentRunner(project_dir, backend=backend)

    result = await runner.run_phase(
        chunk="demo", phase=WorkUnitPhase.PLAN, worktree_path=worktree
    )

    assert result.session_id == "s1"
    assert backend.request is not None
    # The runner builds prompt + sandbox context for the backend.
    assert "SANDBOX RULES" in backend.request.prompt
    assert backend.request.cwd == worktree
    assert backend.request.host_repo_path == runner.host_repo_path
    assert backend.request.expose_review_tool is False


@pytest.mark.asyncio
async def test_run_phase_marks_review_phase_for_review_tool(project_dir, tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    backend = RecordingBackend()
    runner = AgentRunner(project_dir, backend=backend)

    await runner.run_phase(
        chunk="demo", phase=WorkUnitPhase.REVIEW, worktree_path=worktree
    )

    assert backend.request.expose_review_tool is True


@pytest.mark.asyncio
async def test_run_phase_injects_operator_answer(project_dir, tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    backend = RecordingBackend()
    runner = AgentRunner(project_dir, backend=backend)

    await runner.run_phase(
        chunk="demo", phase=WorkUnitPhase.PLAN, worktree_path=worktree, answer="do X"
    )

    assert backend.request.prompt.startswith("Operator feedback: do X")


@pytest.mark.asyncio
async def test_resume_falls_back_to_passed_session_id(project_dir, tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    # Backend returns no session_id; runner should fall back to the passed id.
    backend = RecordingBackend(
        AgentResult(completed=True, suspended=False, session_id=None)
    )
    runner = AgentRunner(project_dir, backend=backend)

    result = await runner.resume_for_active_status(
        chunk="demo", worktree_path=worktree, session_id="orig-sess"
    )

    assert result.session_id == "orig-sess"
    assert backend.request.resume_session_id == "orig-sess"


def test_is_sandbox_violation_blocks_cd_to_host():
    host = Path("/home/user/project")
    worktree = Path("/home/user/project/.ve/chunks/test/worktree")
    violation, reason = is_sandbox_violation("cd /home/user/project && ls", host, worktree)
    assert violation is True
    assert reason is not None


def test_is_sandbox_violation_allows_safe_command():
    host = Path("/home/user/project")
    worktree = Path("/home/user/project/.ve/chunks/test/worktree")
    violation, reason = is_sandbox_violation("git status && ls docs/", host, worktree)
    assert violation is False
    assert reason is None


# ---------------------------------------------------------------------------
# _emit_log_events tests
# ---------------------------------------------------------------------------
# We use SimpleNamespace to simulate SDK message objects without importing
# the Claude Agent SDK (keeping these tests SDK-free).


class TestEmitLogEvents:
    """Tests for _emit_log_events translation of SDK messages to LogEvents."""

    def _collect(self, message) -> list[LogEvent]:
        """Helper: run _emit_log_events and collect emitted events."""
        events: list[LogEvent] = []
        _emit_log_events(message, events.append)
        return events

    def test_text_block_emits_text_event(self):
        """AssistantMessage with a TextBlock emits a TextEvent."""
        from claude_agent_sdk.types import AssistantMessage

        text_block = SimpleNamespace(text="Hello world")
        msg = AssistantMessage(content=[text_block], model="test")

        events = self._collect(msg)
        assert len(events) == 1
        assert isinstance(events[0], TextEvent)
        assert events[0].text == "Hello world"

    def test_tool_use_block_emits_tool_call_event(self):
        """AssistantMessage with a ToolUseBlock emits a ToolCallEvent."""
        from claude_agent_sdk.types import AssistantMessage

        tool_block = SimpleNamespace(
            id="t1", name="Bash", input={"command": "ls", "description": "List files"}
        )
        msg = AssistantMessage(content=[tool_block], model="test")

        events = self._collect(msg)
        assert len(events) == 1
        assert isinstance(events[0], ToolCallEvent)
        assert events[0].tool_id == "t1"
        assert events[0].name == "Bash"
        assert events[0].input == {"command": "ls", "description": "List files"}
        assert events[0].description == "List files"

    def test_tool_result_block_emits_tool_result_event(self):
        """UserMessage with a ToolResultBlock emits a ToolResultEvent."""
        result_block = SimpleNamespace(
            tool_use_id="t1", content="file1.txt", is_error=False
        )
        msg = SimpleNamespace(content=[result_block])

        events = self._collect(msg)
        assert len(events) == 1
        assert isinstance(events[0], ToolResultEvent)
        assert events[0].tool_use_id == "t1"
        assert events[0].content == "file1.txt"
        assert events[0].is_error is False

    def test_result_message_emits_result_event(self):
        """ResultMessage emits a ResultEvent."""
        from claude_agent_sdk.types import ResultMessage

        msg = ResultMessage(
            subtype="success",
            duration_ms=12345,
            duration_api_ms=10000,
            total_cost_usd=0.75,
            num_turns=10,
            is_error=False,
            session_id="sess-1",
            stop_reason="end_turn",
            usage={},
            result="All done",
        )

        events = self._collect(msg)
        assert len(events) == 1
        assert isinstance(events[0], ResultEvent)
        assert events[0].subtype == "success"
        assert events[0].duration_ms == 12345
        assert events[0].total_cost_usd == 0.75
        assert events[0].num_turns == 10
        assert events[0].is_error is False
        assert events[0].session_id == "sess-1"
        assert events[0].result_text == "All done"

    def test_dict_message_emits_nothing(self):
        """Dict messages (e.g. init) are silently skipped."""
        events = self._collect({"type": "init", "session_id": "abc"})
        assert events == []

    def test_mixed_content_emits_multiple_events(self):
        """AssistantMessage with text + tool blocks emits multiple events."""
        from claude_agent_sdk.types import AssistantMessage

        text_block = SimpleNamespace(text="Thinking...")
        tool_block = SimpleNamespace(
            id="t2", name="Read", input={"file_path": "/tmp/foo.py"}
        )
        msg = AssistantMessage(content=[text_block, tool_block], model="test")

        events = self._collect(msg)
        assert len(events) == 2
        assert isinstance(events[0], TextEvent)
        assert isinstance(events[1], ToolCallEvent)
