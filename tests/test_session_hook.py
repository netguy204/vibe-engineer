"""Tests for the plugin SessionStart hook and the ve --version flag.

Verifies the session-start contract defined by the plugin_session_hooks
chunk: the hook is silent outside ve projects, emits a single actionable
hint when the ve CLI is missing, warns on plugin/CLI major.minor version
mismatch (DEC-011), surfaces the current IMPLEMENTING chunk, and never
blocks the session.

# Chunk: docs/chunks/plugin_session_hooks - Plugin SessionStart hook
"""

import importlib.metadata
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from ve import cli

REPO_ROOT = Path(__file__).parent.parent
HOOK_SCRIPT = REPO_ROOT / "hooks" / "session_start.sh"
HOOKS_MANIFEST = REPO_ROOT / "hooks" / "hooks.json"
PLUGIN_MANIFEST = REPO_ROOT / ".claude-plugin" / "plugin.json"

# A PATH that provides standard shell utilities but no `ve` binary.
# ve is distributed via uv tool / pip user installs, never in /usr/bin or /bin.
BARE_PATH = "/usr/bin:/bin"

PLUGIN_VERSION = json.loads(PLUGIN_MANIFEST.read_text())["version"]


def _make_ve_project(tmp_path: Path) -> Path:
    """Create the minimal ve-project signal: docs/trunk/GOAL.md."""
    project = tmp_path / "project"
    (project / "docs" / "trunk").mkdir(parents=True)
    (project / "docs" / "trunk" / "GOAL.md").write_text("# Goal\n")
    return project


def _make_plugin_root(tmp_path: Path, version: str) -> Path:
    """Create a fake plugin root with a plugin.json declaring `version`."""
    root = tmp_path / "plugin_root"
    (root / ".claude-plugin").mkdir(parents=True)
    manifest = {"name": "vibe-engineer", "version": version}
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest, indent=2))
    return root


def _make_ve_stub(
    tmp_path: Path,
    version: str | None = "0.2.0",
    current_chunk: str | None = "docs/chunks/example_chunk",
) -> Path:
    """Write a fake `ve` executable into a tmp bin dir and return that dir.

    version=None simulates a pre-policy CLI where `ve --version` exits 2.
    current_chunk=None simulates "No implementing chunk found" (exit 1).
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    if version is None:
        version_branch = 'echo "Error: No such option: --version" >&2; exit 2'
    else:
        version_branch = f'echo "ve, version {version}"; exit 0'
    if current_chunk is None:
        current_branch = 'echo "No implementing chunk found"; exit 1'
    else:
        current_branch = f'echo "{current_chunk}"; exit 0'
    stub = bin_dir / "ve"
    stub.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "--version" ]; then {version_branch}; fi\n'
        f'if [ "$1" = "chunk" ] && [ "$2" = "list" ] && [ "$3" = "--current" ]; then {current_branch}; fi\n'
        "exit 0\n"
    )
    stub.chmod(0o755)
    return bin_dir


def _run_hook(project_dir: Path, plugin_root: Path, bin_dir: Path | None = None):
    """Run the hook script with a controlled environment."""
    path = BARE_PATH if bin_dir is None else f"{bin_dir}:{BARE_PATH}"
    env = {
        "PATH": path,
        "HOME": os.environ.get("HOME", "/tmp"),
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
    }
    return subprocess.run(
        [str(HOOK_SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestSessionHookProjectDetection:
    def test_silent_in_non_ve_directory(self, tmp_path):
        """Sessions in non-ve directories produce no hook output."""
        project = tmp_path / "not_a_ve_project"
        project.mkdir()
        plugin_root = _make_plugin_root(tmp_path, "0.2.0")
        bin_dir = _make_ve_stub(tmp_path)

        result = _run_hook(project, plugin_root, bin_dir)

        assert result.returncode == 0
        assert result.stdout == ""

    def test_speaks_in_ve_project(self, tmp_path):
        """The same environment inside a ve project produces output."""
        project = _make_ve_project(tmp_path)
        plugin_root = _make_plugin_root(tmp_path, "0.2.0")
        bin_dir = _make_ve_stub(tmp_path, version="0.2.0")

        result = _run_hook(project, plugin_root, bin_dir)

        assert result.returncode == 0
        assert result.stdout != ""


class TestSessionHookCliPresence:
    def test_missing_ve_cli_emits_single_install_hint(self, tmp_path):
        """A missing ve CLI produces one actionable line, not a wall of text."""
        project = _make_ve_project(tmp_path)
        plugin_root = _make_plugin_root(tmp_path, "0.2.0")

        result = _run_hook(project, plugin_root, bin_dir=None)

        assert result.returncode == 0
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        assert len(lines) == 1
        assert "uv tool install vibe-engineer" in lines[0]


class TestSessionHookCurrentChunk:
    def test_surfaces_implementing_chunk(self, tmp_path):
        """Opening a session in a ve project surfaces the IMPLEMENTING chunk."""
        project = _make_ve_project(tmp_path)
        plugin_root = _make_plugin_root(tmp_path, "0.2.0")
        bin_dir = _make_ve_stub(
            tmp_path, version="0.2.0", current_chunk="docs/chunks/example_chunk"
        )

        result = _run_hook(project, plugin_root, bin_dir)

        assert result.returncode == 0
        assert "docs/chunks/example_chunk" in result.stdout
        assert "warning" not in result.stdout.lower()

    def test_no_chunk_line_when_nothing_implementing(self, tmp_path):
        """When no chunk is IMPLEMENTING, no chunk line is emitted."""
        project = _make_ve_project(tmp_path)
        plugin_root = _make_plugin_root(tmp_path, "0.2.0")
        bin_dir = _make_ve_stub(tmp_path, version="0.2.0", current_chunk=None)

        result = _run_hook(project, plugin_root, bin_dir)

        assert result.returncode == 0
        assert "chunk" not in result.stdout.lower()


class TestSessionHookVersionCompatibility:
    """DEC-011: compatible iff plugin and CLI major.minor match."""

    def test_version_mismatch_warns_naming_both_versions(self, tmp_path):
        project = _make_ve_project(tmp_path)
        plugin_root = _make_plugin_root(tmp_path, "0.3.0")
        bin_dir = _make_ve_stub(tmp_path, version="0.2.0")

        result = _run_hook(project, plugin_root, bin_dir)

        assert result.returncode == 0
        assert "0.3.0" in result.stdout
        assert "0.2.0" in result.stdout

    def test_patch_drift_is_silent(self, tmp_path):
        """Same major.minor with different patch levels is compatible."""
        project = _make_ve_project(tmp_path)
        plugin_root = _make_plugin_root(tmp_path, "0.2.5")
        bin_dir = _make_ve_stub(
            tmp_path, version="0.2.0", current_chunk="docs/chunks/example_chunk"
        )

        result = _run_hook(project, plugin_root, bin_dir)

        assert result.returncode == 0
        # Only the chunk line appears; no version warning.
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        assert len(lines) == 1
        assert "example_chunk" in lines[0]

    def test_cli_without_version_flag_warns(self, tmp_path):
        """A pre-policy CLI (no --version) is treated as a mismatch."""
        project = _make_ve_project(tmp_path)
        plugin_root = _make_plugin_root(tmp_path, "0.2.0")
        bin_dir = _make_ve_stub(
            tmp_path, version=None, current_chunk="docs/chunks/example_chunk"
        )

        result = _run_hook(project, plugin_root, bin_dir)

        assert result.returncode == 0
        assert "0.2.0" in result.stdout  # plugin version named in the warning
        assert "upgrade" in result.stdout.lower()
        # The hook still surfaces the chunk; warnings never block.
        assert "docs/chunks/example_chunk" in result.stdout

    def test_output_stays_within_budget(self, tmp_path):
        """Worst case (mismatch warning + chunk line) stays within 3 lines."""
        project = _make_ve_project(tmp_path)
        plugin_root = _make_plugin_root(tmp_path, "1.0.0")
        bin_dir = _make_ve_stub(
            tmp_path, version="0.2.0", current_chunk="docs/chunks/example_chunk"
        )

        result = _run_hook(project, plugin_root, bin_dir)

        assert result.returncode == 0
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        assert 1 <= len(lines) <= 3


class TestHookRegistration:
    def test_hook_script_is_executable(self):
        assert HOOK_SCRIPT.exists(), "hooks/session_start.sh must exist"
        assert os.access(HOOK_SCRIPT, os.X_OK), "hook script must be executable"

    def test_hooks_manifest_registers_session_start(self):
        manifest = json.loads(HOOKS_MANIFEST.read_text())
        session_start = manifest["hooks"]["SessionStart"]
        commands = [
            hook["command"]
            for matcher_group in session_start
            for hook in matcher_group["hooks"]
            if hook["type"] == "command"
        ]
        assert any(
            "${CLAUDE_PLUGIN_ROOT}/hooks/session_start.sh" in command
            for command in commands
        ), "SessionStart must run the session_start.sh script via CLAUDE_PLUGIN_ROOT"


class TestVersionSource:
    def test_ve_version_flag_reports_package_version(self):
        """`ve --version` exists and reports the installed package version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        expected = importlib.metadata.version("vibe-engineer")
        assert expected in result.output
        assert result.output.startswith("ve")

    def test_plugin_and_package_versions_are_coupled(self):
        """DEC-011: plugin.json version equals the pyproject.toml version."""
        pyproject = (REPO_ROOT / "pyproject.toml").read_text()
        match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
        assert match, "pyproject.toml must declare a version"
        assert PLUGIN_VERSION == match.group(1)
