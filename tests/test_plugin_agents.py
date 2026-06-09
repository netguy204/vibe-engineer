"""Tests for the named plugin agents and the commands that reference them.

Inline agent prompts that clear the promotion bar (invoked from more than
one command, or substantial) are versioned once as plugin agents under
agents/ instead of being embedded in command bodies. These tests verify:

1. Generic invariants every agent in agents/ must satisfy (valid
   frontmatter with name/description/tools, no Jinja2 syntax, no
   auto-generated header) — the same static-file discipline that governs
   commands/ (DEC-010).
2. The two promoted roles exist: chunk-executor (narrative-execute's wave
   execution) and intent-auditor (audit-intent's fan-out).
3. The rewired commands reference the agents by name and no longer embed
   the promoted prompt bodies inline, and the load-bearing protocol rules
   survived the move into the agent definitions.

# Chunk: docs/chunks/plugin_subagents - Named plugin agents for parallelizable workflow roles
"""

import pytest

from test_plugin_manifest import REPO_ROOT, _parse_frontmatter

AGENTS_DIR = REPO_ROOT / "agents"
COMMANDS_DIR = REPO_ROOT / "commands"

CHUNK_EXECUTOR = AGENTS_DIR / "chunk-executor.md"
INTENT_AUDITOR = AGENTS_DIR / "intent-auditor.md"
NARRATIVE_EXECUTE = COMMANDS_DIR / "narrative-execute.md"
AUDIT_INTENT = COMMANDS_DIR / "audit-intent.md"


def _agent_files() -> list:
    return sorted(AGENTS_DIR.glob("*.md"))


def _agent_ids() -> list[str]:
    return [p.name for p in _agent_files()]


@pytest.mark.parametrize("agent_file", _agent_files(), ids=_agent_ids())
class TestAgentInvariants:
    """Invariants every plugin agent file must satisfy."""

    def test_frontmatter_has_name_description_tools(self, agent_file):
        frontmatter = _parse_frontmatter(agent_file)
        assert frontmatter.get("name") == agent_file.stem, (
            f"{agent_file.name}: frontmatter name must match the file stem"
        )
        assert frontmatter.get("description"), (
            f"{agent_file.name}: frontmatter description must be non-empty"
        )
        assert frontmatter.get("tools"), (
            f"{agent_file.name}: agents must declare appropriate tool access"
        )

    def test_no_jinja2_syntax(self, agent_file):
        """Plugin agents are static — render-time syntax must not appear."""
        text = agent_file.read_text()
        for marker in ("{%", "{{", "{#"):
            assert marker not in text, (
                f"{agent_file.name}: contains Jinja2 syntax {marker!r}"
            )

    def test_no_auto_generated_header(self, agent_file):
        """Plugin files are the source, not render output."""
        assert "AUTO-GENERATED" not in agent_file.read_text(), (
            f"{agent_file.name}: carries the obsolete auto-generated header"
        )

    def test_carries_chunk_backreference(self, agent_file):
        assert "docs/chunks/plugin_subagents" in agent_file.read_text(), (
            f"{agent_file.name}: must trace back to the chunk that promoted it"
        )


class TestPromotedAgentsExist:
    """GOAL success criterion: agents/ contains at least chunk-executor and
    intent-auditor definitions."""

    def test_chunk_executor_exists(self):
        assert CHUNK_EXECUTOR.is_file()

    def test_intent_auditor_exists(self):
        assert INTENT_AUDITOR.is_file()

    def test_gitkeep_placeholder_removed(self):
        assert not (AGENTS_DIR / ".gitkeep").exists(), (
            "agents/ has real content; the scaffold placeholder is obsolete"
        )


class TestChunkExecutorPromotion:
    """narrative-execute references the chunk-executor agent instead of
    embedding the lifecycle prompt inline."""

    def test_agent_carries_lifecycle(self):
        body = CHUNK_EXECUTOR.read_text()
        for step in (
            "/chunk-plan",
            "/chunk-implement",
            "/chunk-review",
            "/chunk-complete",
        ):
            assert step in body, f"chunk-executor must run {step}"
        assert "3 times maximum" in body, (
            "the implement/review retry cap must survive the promotion"
        )

    def test_agent_carries_report_contract(self):
        body = CHUNK_EXECUTOR.read_text()
        assert "SUCCESS" in body
        assert "FAILURE" in body

    def test_command_references_agent(self):
        assert "chunk-executor" in NARRATIVE_EXECUTE.read_text()

    def test_command_no_longer_embeds_prompt(self):
        body = NARRATIVE_EXECUTE.read_text()
        assert "You are executing chunk" not in body, (
            "the inline lifecycle prompt must live in the agent, not the command"
        )

    def test_command_keeps_wave_mechanics(self):
        """The rewire replaces the prompt, not the orchestration."""
        body = NARRATIVE_EXECUTE.read_text()
        assert "run_in_background" in body
        assert "ve chunk activate" in body


class TestIntentAuditorPromotion:
    """audit-intent references the intent-auditor agent instead of
    embedding the sub-agent protocol inline."""

    def test_agent_carries_load_bearing_rules(self):
        body = INTENT_AUDITOR.read_text()
        assert "Veto rule" in body, (
            "the veto rule is load-bearing and must survive the promotion"
        )
        assert "Symmetric verification" in body
        assert "action_taken" in body, "the return format must survive"
        assert "Do NOT commit" in body, (
            "the working-tree-only constraint must survive"
        )

    def test_command_references_agent(self):
        assert "intent-auditor" in AUDIT_INTENT.read_text()

    def test_command_no_longer_embeds_protocol(self):
        body = AUDIT_INTENT.read_text()
        assert "Veto rule" not in body, (
            "the sub-agent protocol must live in the agent, not the command"
        )
        assert "Sub-agent prompt template" not in body

    def test_command_keeps_orchestration(self):
        """Wave mechanics and orchestrator notes stay with the command."""
        body = AUDIT_INTENT.read_text()
        assert "10 batches of 5" in body
        assert "Notes for the orchestrating agent" in body
