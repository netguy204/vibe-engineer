"""Tests for ported plugin commands and the runtime context-detection convention.

Plugin command files are static markdown (DEC-010): behavior the template
system resolved at render time must be resolved at execution time. These
tests verify two layers:

1. Generic invariants every skill in skills/ must satisfy (no Jinja2
   syntax, no auto-generated header, valid frontmatter). These give the
   wave-3 mass ports (plugin_core_commands, plugin_orch_commands) standing
   regression coverage.
2. The chunk-create pilot: runtime detection of .ve-task.yaml (task context)
   and .ve-config.yaml (project config), preservation of the task-context
   guidance as runtime conditionals, and a behavioral check that the
   preamble's shell lines distinguish the three runtime situations.

# Chunk: docs/chunks/plugin_runtime_context - Runtime context-detection convention
"""

import re
import subprocess

import pytest
import yaml

from test_plugin_manifest import REPO_ROOT, _parse_frontmatter

SKILLS_DIR = REPO_ROOT / "skills"
CHUNK_CREATE = SKILLS_DIR / "chunk-create" / "SKILL.md"


def _command_files() -> list:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def _command_ids() -> list[str]:
    # In the per-skill layout every file is SKILL.md; the directory is the name.
    return [p.parent.name for p in _command_files()]


@pytest.mark.parametrize("command_file", _command_files(), ids=_command_ids())
class TestCommandInvariants:
    """Invariants every plugin command file must satisfy."""

    def test_frontmatter_has_name_and_description(self, command_file):
        frontmatter = _parse_frontmatter(command_file)
        assert frontmatter.get("name") == command_file.parent.name, (
            f"{command_file.parent.name}: frontmatter name must match the "
            "skill directory name"
        )
        assert frontmatter.get("description"), (
            f"{command_file.name}: frontmatter description must be non-empty"
        )

    def test_no_jinja2_syntax(self, command_file):
        """Plugin commands are static — render-time syntax must not survive."""
        text = command_file.read_text()
        for marker in ("{%", "{{", "{#"):
            assert marker not in text, (
                f"{command_file.name}: contains Jinja2 syntax {marker!r}; "
                "render-time conditionals must become runtime instructions"
            )

    def test_no_auto_generated_header(self, command_file):
        """Plugin files must never carry the legacy init-render header.

        src/project.py#_is_ve_generated_file keys on the old
        "AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY" header for legacy
        cleanup, so the substring is rejected wholesale. Files rendered at
        build time from src/templates/plugin/ carry the distinct
        "GENERATED from src/templates/plugin/..." marker instead, which
        tests/test_plugin_render.py requires per rendered file.

        # Chunk: docs/chunks/dualplugin_template_source - Marker collision guard
        """
        assert "AUTO-GENERATED" not in command_file.read_text(), (
            f"{command_file.name}: carries the obsolete auto-generated header"
        )


class TestChunkCreateCommand:
    """The chunk-create pilot port (plugin_runtime_context success criteria)."""

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
        """The command's own behavior must carry over unchanged."""
        body = CHUNK_CREATE.read_text()
        assert "intent-bearing" in body
        assert "ve chunk create" in body


def _extract_context_shell_lines(path) -> list[str]:
    """Pull the !`...` shell commands out of a command's Context block."""
    return re.findall(r"!`([^`]+)`", path.read_text())


def _run_context_lines(lines: list[str], cwd) -> str:
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


class TestRuntimeDetection:
    """The preamble's shell lines must distinguish the three runtime
    situations the success criteria name: plain project, project with
    .ve-config.yaml, and task workspace with .ve-task.yaml."""

    @pytest.fixture
    def context_lines(self):
        lines = _extract_context_shell_lines(CHUNK_CREATE)
        assert lines, "chunk-create must have !-prefixed context lines"
        # Drop the ve CLI probe — its result depends on the host, not on
        # the directory contents under test.
        return [line for line in lines if "ve --help" not in line]

    def test_plain_project(self, context_lines, tmp_path):
        output = _run_context_lines(context_lines, tmp_path)
        assert "not a task workspace" in output
        assert "external_artifact_repo" not in output
        assert "cluster_subsystem_threshold" not in output

    def test_project_with_config(self, context_lines, tmp_path):
        (tmp_path / ".ve-config.yaml").write_text(
            "cluster_subsystem_threshold: 3\n"
        )
        output = _run_context_lines(context_lines, tmp_path)
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
        output = _run_context_lines(context_lines, tmp_path)
        assert "external_artifact_repo" in output
        assert "task-artifacts" in output
        assert "proj-a" in output, (
            "the projects list must surface — it replaces the "
            "{% for project in projects %} render loop"
        )
