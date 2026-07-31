"""Tests for ported plugin commands and the runtime context-detection convention.

Plugin command files are static markdown (DEC-010): behavior the template
system resolved at render time must be resolved at execution time. These
tests verify two layers:

1. Generic invariants every command in commands/ must satisfy (no Jinja2
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

COMMANDS_DIR = REPO_ROOT / "commands"
CHUNK_CREATE = COMMANDS_DIR / "chunk-create.md"


def _command_files() -> list:
    return sorted(COMMANDS_DIR.glob("*.md"))


def _command_ids() -> list[str]:
    return [p.name for p in _command_files()]


@pytest.mark.parametrize("command_file", _command_files(), ids=_command_ids())
class TestCommandInvariants:
    """Invariants every plugin command file must satisfy."""

    def test_frontmatter_has_name_and_description(self, command_file):
        frontmatter = _parse_frontmatter(command_file)
        assert frontmatter.get("name") == command_file.stem, (
            f"{command_file.name}: frontmatter name must match the file stem"
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
        """Plugin files are the source, not render output."""
        assert "AUTO-GENERATED" not in command_file.read_text(), (
            f"{command_file.name}: carries the obsolete auto-generated header"
        )

    # Chunk: docs/chunks/hooks_lifecycle_fragments - Universal VE hook wiring
    def test_context_block_loads_the_project_hook(self, command_file):
        """Every command exposes docs/hooks/<name>.md at its inflection point.

        Universal wiring is what removes the need for a hand-maintained
        allowlist: the set of valid hook events is exactly the set of commands.
        A new command added without this line silently has no hook support.
        """
        text = command_file.read_text()
        expected = (
            f'!`ve hooks show {command_file.stem} 2>/dev/null '
            '|| echo "(no project hook)"`'
        )
        assert expected in text, (
            f"{command_file.name}: missing the guarded hook context line {expected!r}"
        )

    # Chunk: docs/chunks/hooks_lifecycle_fragments - Universal VE hook wiring
    def test_hook_command_is_permitted(self, command_file):
        """Without the allowed-tools entry the context line prompts or fails
        rather than resolving — a silent failure of the whole mechanism."""
        allowed = _parse_frontmatter(command_file).get("allowed-tools", "")
        assert "Bash(ve hooks show:*)" in allowed, (
            f"{command_file.name}: allowed-tools must permit Bash(ve hooks show:*)"
        )

    # Chunk: docs/chunks/hooks_lifecycle_fragments - Universal VE hook wiring
    def test_runtime_context_explains_the_hook(self, command_file):
        """The context line alone doesn't tell the agent what to do with the
        content; the interpretation bullet carries the binding-instruction and
        conflict-surfacing rules."""
        text = command_file.read_text()
        assert "**Project hook**" in text, (
            f"{command_file.name}: missing the Project hook runtime-context bullet"
        )


# Chunk: docs/chunks/hooks_lifecycle_fragments - Known-event vocabulary pinned to disk
class TestHookEventVocabulary:
    """hooks.KNOWN_EVENTS must equal the plugin's command names.

    The constant is a literal because the ve CLI is installed separately from
    the plugin (DEC-010) and cannot reliably read commands/ at runtime. Exact
    equality in both directions is what keeps that literal honest.
    """

    def test_known_events_matches_command_files_exactly(self):
        from hooks import KNOWN_EVENTS

        on_disk = {path.stem for path in _command_files()}

        assert KNOWN_EVENTS == on_disk, (
            "hooks.KNOWN_EVENTS is out of sync with commands/*.md. "
            f"Missing from KNOWN_EVENTS: {sorted(on_disk - KNOWN_EVENTS)}. "
            f"Stale entries in KNOWN_EVENTS: {sorted(KNOWN_EVENTS - on_disk)}."
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


# Chunk: docs/chunks/hooks_lifecycle_fragments - Hook context line survives an older CLI
class TestHookContextLineIsGuarded:
    """The hook context line runs inside every command's context block, so it
    must stay clean even when the installed CLI predates the `hooks` command
    (DEC-011 lets the plugin and CLI version independently)."""

    def _stub_old_ve(self, tmp_path):
        """A `ve` that rejects `hooks` the way real Click does: usage error to
        stderr, exit 2."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        stub = bin_dir / "ve"
        stub.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "hooks" ]; then\n'
            '  echo "Usage: ve [OPTIONS] COMMAND [ARGS]..." >&2\n'
            "  echo \"Error: No such command 'hooks'.\" >&2\n"
            "  exit 2\n"
            "fi\n"
            "exit 0\n"
        )
        stub.chmod(0o755)
        return bin_dir

    def _hook_line(self, path):
        lines = [
            line for line in _extract_context_shell_lines(path) if "ve hooks show" in line
        ]
        assert len(lines) == 1, f"{path.name}: expected exactly one hook context line"
        return lines[0]

    def test_older_cli_yields_the_absent_hook_fallback_not_an_error(self, tmp_path):
        bin_dir = self._stub_old_ve(tmp_path)
        line = self._hook_line(CHUNK_CREATE)

        result = subprocess.run(
            ["bash", "-c", line],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env={"PATH": f"{bin_dir}:/usr/bin:/bin"},
        )

        # What the agent sees is stdout; it must be the benign fallback...
        assert result.stdout.strip() == "(no project hook)"
        # ...and the Click usage error must not surface anywhere.
        assert "No such command" not in result.stdout
        assert "No such command" not in result.stderr
        assert result.returncode == 0

    def test_every_command_hook_line_carries_the_guard(self):
        """The behavioral check above runs one command; this pins the guard on
        all of them so a future port cannot drop it."""
        for path in _command_files():
            line = self._hook_line(path)
            assert '2>/dev/null || echo "(no project hook)"' in line, (
                f"{path.name}: hook context line is missing the older-CLI guard"
            )


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
