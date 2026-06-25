# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_seam - Unit tests for the AgentBackend seam
"""Tests for the backend-agnostic AgentBackend seam.

These cover the contract types and that AgentRunner delegates to an injected
backend (proving the seam is real and swappable), independent of any SDK.
"""

from pathlib import Path

import pytest

from orchestrator.agent import AgentRunner
from orchestrator.backend import (
    AgentBackend,
    SessionRequest,
    ToolDecision,
    ToolUse,
    is_sandbox_violation,
)
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
