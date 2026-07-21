"""Tests for the plugin's cross-harness skills and the runtime
context-detection convention.

The plugin ships the entire agent-facing workflow as cross-harness skills:
skills/<name>/SKILL.md (agentskills.io layout). Skill files are static
markdown (DEC-010, as amended by plugin_crossharness_skills): behavior the
template system once resolved at render time — and context Claude Code's
slash-command preprocessing once resolved at invocation time — must be
resolved at execution time by instructing the agent to run commands. These
tests verify three layers:

1. Generic invariants every skill in skills/ must satisfy (no Jinja2
   syntax, no auto-generated header, no Claude-Code-only !`...`
   preprocessing, valid frontmatter) — plus the boundary invariant that
   commands/ ships no workflow content.
2. The chunk-create pilot: runtime detection of .ve-task.yaml (task
   context) and .ve-config.yaml (project config), preservation of the
   task-context guidance as runtime conditionals.
3. A behavioral check that the instructed context-gathering shell lines
   distinguish the three runtime situations.

# Chunk: docs/chunks/plugin_runtime_context - Runtime context-detection convention
# Chunk: docs/chunks/plugin_crossharness_skills - Cross-harness skills layout
"""

import re
import subprocess

import pytest
import yaml

from test_plugin_manifest import REPO_ROOT, _parse_frontmatter

SKILLS_DIR = REPO_ROOT / "skills"
COMMANDS_DIR = REPO_ROOT / "commands"
CHUNK_CREATE = SKILLS_DIR / "chunk-create" / "SKILL.md"


def _skill_files() -> list:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def _skill_ids() -> list[str]:
    return [p.parent.name for p in _skill_files()]


def test_skills_directory_has_content():
    assert _skill_files(), "skills/ must ship the workflow content"


def test_commands_ships_no_workflow_content():
    """commands/ is reserved for genuinely command-shaped future UX."""
    stray = sorted(COMMANDS_DIR.glob("**/*.md"))
    assert not stray, (
        "commands/ must ship no workflow content; found "
        + ", ".join(str(p.relative_to(REPO_ROOT)) for p in stray)
    )


@pytest.mark.parametrize("skill_file", _skill_files(), ids=_skill_ids())
class TestSkillInvariants:
    """Invariants every plugin skill file must satisfy."""

    def test_frontmatter_name_matches_directory(self, skill_file):
        frontmatter = _parse_frontmatter(skill_file)
        assert frontmatter.get("name") == skill_file.parent.name, (
            f"{skill_file.parent.name}: frontmatter name must match the "
            "skill directory name"
        )
        assert frontmatter.get("description"), (
            f"{skill_file.parent.name}: frontmatter description must be non-empty"
        )

    def test_no_jinja2_syntax(self, skill_file):
        """Plugin skills are static — render-time syntax must not survive."""
        text = skill_file.read_text()
        for marker in ("{%", "{{", "{#"):
            assert marker not in text, (
                f"{skill_file.parent.name}: contains Jinja2 syntax {marker!r}; "
                "render-time conditionals must become runtime instructions"
            )

    def test_no_auto_generated_header(self, skill_file):
        """Plugin files are the source, not render output."""
        assert "AUTO-GENERATED" not in skill_file.read_text(), (
            f"{skill_file.parent.name}: carries the obsolete auto-generated header"
        )

    def test_self_contained_no_dynamic_preprocessing(self, skill_file):
        """Skills must not depend on Claude Code's !`...` slash-command
        preprocessing — other harnesses (and Claude Code's own Skill-tool
        invocation path) do not execute it. Context gathering must be
        expressed as explicit instructions to run commands."""
        text = skill_file.read_text()
        assert "!`" not in text, (
            f"{skill_file.parent.name}: uses !`...` dynamic preprocessing; "
            "convert it to explicit gather-context instructions"
        )


class TestChunkCreateSkill:
    """The chunk-create pilot (plugin_runtime_context success criteria)."""

    def test_exists_with_frontmatter(self):
        frontmatter = _parse_frontmatter(CHUNK_CREATE)
        assert frontmatter["name"] == "chunk-create"
        assert frontmatter["description"]

    def test_detects_task_context_at_runtime(self):
        """Replaces the {% if task_context %} render variant."""
        body = CHUNK_CREATE.read_text()
        assert ".ve-task.yaml" in body, (
            "chunk-create must detect task context via .ve-task.yaml"
        )

    def test_reads_project_config_at_runtime(self):
        """Replaces render-time ve_config injection."""
        body = CHUNK_CREATE.read_text()
        assert ".ve-config.yaml" in body, (
            "chunk-create must read project config via .ve-config.yaml"
        )

    def test_preserves_task_context_guidance(self):
        """The external-artifact-repo routing from the template's
        {% if task_context %} block must survive as a runtime conditional,
        not be dropped."""
        body = CHUNK_CREATE.read_text()
        assert "external_artifact_repo" in body, (
            "task-context guidance must reference the external_artifact_repo "
            "key from .ve-task.yaml"
        )
        assert "external artifact repo" in body.lower(), (
            "the external artifact repo routing guidance must be preserved"
        )

    def test_keeps_arguments_placeholder(self):
        assert "$ARGUMENTS" in CHUNK_CREATE.read_text()

    def test_carries_chunk_backreference(self):
        assert "docs/chunks/plugin_runtime_context" in CHUNK_CREATE.read_text()

    def test_keeps_intent_judgment_gate(self):
        """The skill's own behavior must carry over unchanged."""
        body = CHUNK_CREATE.read_text()
        assert "intent-bearing" in body
        assert "ve chunk create" in body


def _extract_context_shell_lines(path) -> list[str]:
    """Pull the instructed shell commands out of a skill's Context block.

    Self-contained skills express context gathering as list items of the
    form ``- <label>: `<shell command>` `` under the ``## Context``
    heading (plugin_crossharness_skills)."""
    text = path.read_text()
    match = re.search(r"^## Context\n(.*?)(?=^## )", text, re.DOTALL | re.MULTILINE)
    assert match, f"{path}: no ## Context section"
    return re.findall(r"^- [^:`]+: `([^`]+)`", match.group(1), re.MULTILINE)


class TestRuntimeDetection:
    """The instructed context-gathering shell lines must distinguish the
    three runtime situations the success criteria name: plain project,
    project with .ve-config.yaml, and task workspace with .ve-task.yaml."""

    @pytest.fixture
    def context_lines(self):
        lines = _extract_context_shell_lines(CHUNK_CREATE)
        assert lines, "chunk-create must instruct context-gathering commands"
        # Drop the ve CLI probe — its result depends on the host, not on
        # the directory contents under test.
        return [line for line in lines if "ve --help" not in line]

    def _run_context_lines(self, lines: list[str], cwd) -> str:
        output = []
        for line in lines:
            result = subprocess.run(
                ["bash", "-c", line],
                cwd=cwd,
                capture_output=True,
                text=True,
            )
            output.append(result.stdout)
        return "\n".join(output)

    def test_plain_project(self, context_lines, tmp_path):
        output = self._run_context_lines(context_lines, tmp_path)
        assert "not a task workspace" in output
        assert "external_artifact_repo" not in output
        assert "cluster_subsystem_threshold" not in output

    def test_project_with_config(self, context_lines, tmp_path):
        (tmp_path / ".ve-config.yaml").write_text(
            "cluster_subsystem_threshold: 3\n"
        )
        output = self._run_context_lines(context_lines, tmp_path)
        assert "cluster_subsystem_threshold: 3" in output, (
            "config contents must surface so the agent sees the real values"
        )
        assert "not a task workspace" in output

    def test_task_workspace(self, context_lines, tmp_path):
        (tmp_path / ".ve-task.yaml").write_text(
            yaml.dump(
                {
                    "external_artifact_repo": "task-artifacts",
                    "projects": ["proj-a", "proj-b"],
                }
            )
        )
        output = self._run_context_lines(context_lines, tmp_path)
        assert "external_artifact_repo" in output
        assert "task-artifacts" in output
        assert "proj-a" in output, (
            "the projects list must surface — it replaces the "
            "{% for project in projects %} render loop"
        )
