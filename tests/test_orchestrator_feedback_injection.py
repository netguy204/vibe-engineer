# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_review_feedback_fidelity - Tests for review feedback injection
"""Tests for review feedback injection into the implementer prompt.

Verifies that:
- REVIEW_FEEDBACK.md content is prepended to the IMPLEMENT phase prompt
- No injection occurs when REVIEW_FEEDBACK.md doesn't exist (first iteration)
- The injected content includes a clear header
- The chunk-implement template includes feedback instructions
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from orchestrator.agent import (
    AgentRunner,
    PHASE_SKILL_FILES,
    _load_skill_content,
)
from orchestrator.models import AgentResult, WorkUnitPhase


class MockClaudeSDKClient:
    """Mock for ClaudeSDKClient for testing prompt content."""

    last_instance = None

    def __init__(self, options=None):
        self.options = options
        self._query_prompt = None
        MockClaudeSDKClient.last_instance = self

    @classmethod
    def reset(cls):
        cls.last_instance = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def query(self, prompt):
        self._query_prompt = prompt

    async def receive_response(self):
        from claude_agent_sdk.types import ResultMessage

        msg = MagicMock(spec=ResultMessage)
        msg.result = "Success"
        msg.is_error = False
        msg.session_id = None
        yield msg


@pytest.fixture
def project_dir(tmp_path):
    """Create a project directory with skill files for testing."""
    # Create .agents/skills directory structure (canonical location)
    skills_dir = tmp_path / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    # Create .claude/commands directory for backwards-compat symlinks
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

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


class TestFeedbackInjectionIntoPrompt:
    """Tests for feedback content injection into the implementer prompt."""

    @pytest.mark.asyncio
    async def test_feedback_prepended_when_file_exists(self, project_dir, tmp_path):
        """When REVIEW_FEEDBACK.md exists, its content is prepended to the prompt."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create the feedback file
        chunk_dir = worktree_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        feedback_content = """# Review Feedback

**Iteration:** 1
**Decision:** FEEDBACK

## Summary

Multiple issues found.

## Issues to Address

### Issue 1: src/main.py:42

**Concern:** Missing error handling

**Suggestion:** Add try/except block

### Issue 2: README.md

**Concern:** Documentation not updated
"""
        (chunk_dir / "REVIEW_FEEDBACK.md").write_text(feedback_content)

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MockClaudeSDKClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.IMPLEMENT,
                worktree_path=worktree_path,
            )

        client = MockClaudeSDKClient.last_instance
        assert client is not None
        prompt = client._query_prompt

        # Verify the feedback header is in the prompt
        assert "## Prior Review Feedback (MUST ADDRESS)" in prompt

        # Verify the feedback content is in the prompt
        assert "Missing error handling" in prompt
        assert "Documentation not updated" in prompt

        # Verify instructions for addressing feedback
        assert "Fix it in the code" in prompt
        assert "Defer it with a clear reason" in prompt
        assert "Dispute it with evidence" in prompt
        assert "Non-functional feedback" in prompt

    @pytest.mark.asyncio
    async def test_no_injection_when_feedback_missing(self, project_dir, tmp_path):
        """When REVIEW_FEEDBACK.md doesn't exist, prompt is unchanged."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create chunk dir but NO feedback file
        chunk_dir = worktree_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MockClaudeSDKClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.IMPLEMENT,
                worktree_path=worktree_path,
            )

        client = MockClaudeSDKClient.last_instance
        prompt = client._query_prompt

        # Should NOT contain feedback header
        assert "Prior Review Feedback" not in prompt

    @pytest.mark.asyncio
    async def test_no_injection_for_non_implement_phases(self, project_dir, tmp_path):
        """Feedback injection only happens for IMPLEMENT phase."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Create feedback file that shouldn't be read for PLAN phase
        chunk_dir = worktree_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "REVIEW_FEEDBACK.md").write_text("# Some feedback")

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MockClaudeSDKClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
            )

        client = MockClaudeSDKClient.last_instance
        prompt = client._query_prompt

        assert "Prior Review Feedback" not in prompt

    @pytest.mark.asyncio
    async def test_feedback_comes_before_skill_content(self, project_dir, tmp_path):
        """Feedback is prepended before the skill content."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        chunk_dir = worktree_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "REVIEW_FEEDBACK.md").write_text("# Review feedback here")

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MockClaudeSDKClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.IMPLEMENT,
                worktree_path=worktree_path,
            )

        client = MockClaudeSDKClient.last_instance
        prompt = client._query_prompt

        # The feedback header should appear before the CWD reminder
        # (feedback is prepended to prompt, then CWD is prepended on top)
        # Actually, feedback is prepended first, then CWD is prepended
        # So order is: CWD reminder -> feedback header -> feedback content -> skill content
        feedback_pos = prompt.find("Prior Review Feedback")
        skill_pos = prompt.find("Instructions")
        assert feedback_pos < skill_pos, "Feedback should appear before skill instructions"


class TestImplementTemplateIncludesFeedbackInstructions:
    """Tests verifying the chunk-implement template includes feedback instructions."""

    def test_template_mentions_review_feedback(self):
        """The chunk-implement template references REVIEW_FEEDBACK.md."""
        template_path = Path(__file__).parent.parent / "src" / "templates" / "commands" / "chunk-implement.md.jinja2"
        content = template_path.read_text()

        assert "REVIEW_FEEDBACK.md" in content

    def test_template_instructs_addressing_all_issues(self):
        """The template instructs implementer to address every issue."""
        template_path = Path(__file__).parent.parent / "src" / "templates" / "commands" / "chunk-implement.md.jinja2"
        content = template_path.read_text()

        assert "MUST address EVERY issue" in content

    def test_template_mentions_non_functional_feedback(self):
        """The template mentions non-functional feedback importance."""
        template_path = Path(__file__).parent.parent / "src" / "templates" / "commands" / "chunk-implement.md.jinja2"
        content = template_path.read_text()

        assert "Non-functional feedback" in content

    def test_template_instructs_delete_feedback_file(self):
        """The template instructs deleting the feedback file after addressing."""
        template_path = Path(__file__).parent.parent / "src" / "templates" / "commands" / "chunk-implement.md.jinja2"
        content = template_path.read_text()

        assert "delete" in content.lower()
        assert "REVIEW_FEEDBACK.md" in content

    def test_template_mentions_fix_defer_dispute(self):
        """The template lists the three valid responses to feedback items."""
        template_path = Path(__file__).parent.parent / "src" / "templates" / "commands" / "chunk-implement.md.jinja2"
        content = template_path.read_text()

        assert "Fix" in content
        assert "Defer" in content
        assert "Dispute" in content
