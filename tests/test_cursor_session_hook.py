"""Tests for the Cursor sessionStart hook adapter.

The Cursor plugin registers .cursor-plugin/hooks/session_start.sh for the
`sessionStart` event. Cursor hooks speak JSON over stdio, so the adapter
wraps the shared session-start core (hooks/session_start.sh) and emits
{"additional_context": ...} — the field Cursor adds to the conversation's
initial system context — or {} when the core is silent. These tests verify
the translation layer and the registration chain; the core's own behavior
(bootstrap, drift, chunk surfacing) is covered by test_session_hook.py and
is exercised here only enough to prove it flows through unchanged.

# Chunk: docs/chunks/dualplugin_lifecycle_release - Cursor session hook
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CORE_SCRIPT = REPO_ROOT / "hooks" / "session_start.sh"
ADAPTER_SCRIPT = REPO_ROOT / ".cursor-plugin" / "hooks" / "session_start.sh"
CURSOR_HOOKS_CONFIG = REPO_ROOT / ".cursor-plugin" / "hooks" / "hooks.json"
CURSOR_PLUGIN_MANIFEST = REPO_ROOT / ".cursor-plugin" / "plugin.json"

# A PATH with standard shell utilities but no `ve` binary (see
# test_session_hook.py for the rationale).
BARE_PATH = "/usr/bin:/bin"

PLUGIN_VERSION = json.loads(CURSOR_PLUGIN_MANIFEST.read_text())["version"]


def _make_plugin_root(
    tmp_path: Path,
    version: str = PLUGIN_VERSION,
    claude_manifest: bool = True,
    cursor_manifest: bool = True,
) -> Path:
    """Copy the real scripts into a plugin-shaped tree under tmp_path.

    The adapter locates the plugin root from its own path, so behavioral
    tests must run it from a layout with the real relative structure:
    hooks/session_start.sh (core) and .cursor-plugin/hooks/session_start.sh
    (adapter) under one root.
    """
    root = tmp_path / "plugin_root"
    (root / "hooks").mkdir(parents=True)
    (root / ".cursor-plugin" / "hooks").mkdir(parents=True)
    shutil.copy(CORE_SCRIPT, root / "hooks" / "session_start.sh")
    shutil.copy(
        ADAPTER_SCRIPT, root / ".cursor-plugin" / "hooks" / "session_start.sh"
    )
    manifest = json.dumps({"name": "vibe-engineer", "version": version})
    if claude_manifest:
        (root / ".claude-plugin").mkdir()
        (root / ".claude-plugin" / "plugin.json").write_text(manifest)
    if cursor_manifest:
        (root / ".cursor-plugin" / "plugin.json").write_text(manifest)
    return root


def _make_ve_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "docs" / "trunk").mkdir(parents=True)
    (project / "docs" / "trunk" / "GOAL.md").write_text("# Goal\n")
    return project


def _make_ve_stub(
    tmp_path: Path,
    version: str = PLUGIN_VERSION,
    current_chunk: str | None = "docs/chunks/example_chunk",
) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    if current_chunk is None:
        current_branch = 'echo "No implementing chunk found"; exit 1'
    else:
        current_branch = f"echo '{current_chunk}'; exit 0"
    stub = bin_dir / "ve"
    stub.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "--version" ]; then echo "ve, version {version}"; exit 0; fi\n'
        f'if [ "$1" = "chunk" ] && [ "$2" = "list" ] && [ "$3" = "--current" ]; then {current_branch}; fi\n'
        "exit 0\n"
    )
    stub.chmod(0o755)
    return bin_dir


def _run_adapter(
    plugin_root: Path,
    project_dir: Path,
    bin_dir: Path | None = None,
    extra_env: dict[str, str] | None = None,
):
    """Run the copied adapter the way Cursor would: CURSOR_* env only."""
    path = BARE_PATH if bin_dir is None else f"{bin_dir}:{BARE_PATH}"
    env = {
        "PATH": path,
        "HOME": os.environ.get("HOME", "/tmp"),
        "CURSOR_PROJECT_DIR": str(project_dir),
    }
    if extra_env:
        env.update(extra_env)
    adapter = plugin_root / ".cursor-plugin" / "hooks" / "session_start.sh"
    return subprocess.run(
        [str(adapter)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )


class TestAdapterOutputContract:
    """Every run yields exactly one JSON object and exit 0."""

    def test_silent_core_yields_empty_object(self, tmp_path):
        """Outside a ve project the core says nothing; the adapter must still
        answer with valid JSON, not empty output."""
        plugin_root = _make_plugin_root(tmp_path)
        not_a_project = tmp_path / "plain"
        not_a_project.mkdir()

        result = _run_adapter(plugin_root, not_a_project, _make_ve_stub(tmp_path))

        assert result.returncode == 0
        assert json.loads(result.stdout) == {}

    def test_core_output_arrives_as_additional_context(self, tmp_path):
        plugin_root = _make_plugin_root(tmp_path)
        project = _make_ve_project(tmp_path)
        bin_dir = _make_ve_stub(tmp_path, current_chunk="docs/chunks/example_chunk")

        result = _run_adapter(plugin_root, project, bin_dir)

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert "docs/chunks/example_chunk" in payload["additional_context"]

    def test_multiline_output_with_quotes_stays_valid_json(self, tmp_path):
        """Worst case: a drift warning plus a chunk line containing a double
        quote. The escaping, not the content, is under test."""
        plugin_root = _make_plugin_root(tmp_path, version="9.9.9")
        project = _make_ve_project(tmp_path)
        bin_dir = _make_ve_stub(
            tmp_path,
            version="0.1.0",
            current_chunk='docs/chunks/example_"quoted"_chunk',
        )

        result = _run_adapter(plugin_root, project, bin_dir)

        assert result.returncode == 0
        payload = json.loads(result.stdout)
        context = payload["additional_context"]
        assert "\n" in context, "core emitted two lines; both must survive"
        assert 'example_"quoted"_chunk' in context
        assert "9.9.9" in context and "0.1.0" in context

    def test_missing_core_degrades_to_empty_object(self, tmp_path):
        """A broken install (adapter present, core missing) must not break
        the session: sessionStart may not fail loudly."""
        plugin_root = _make_plugin_root(tmp_path)
        (plugin_root / "hooks" / "session_start.sh").unlink()
        project = _make_ve_project(tmp_path)

        result = _run_adapter(plugin_root, project, _make_ve_stub(tmp_path))

        assert result.returncode == 0
        assert json.loads(result.stdout) == {}


class TestPluginRootResolution:
    def test_resolves_root_from_own_location(self, tmp_path):
        """No CURSOR_PLUGIN_ROOT in the environment: the adapter's own path
        names the root. The spec leaves plugin-hook CWD undefined, so this
        must not depend on where the process starts."""
        plugin_root = _make_plugin_root(tmp_path)
        project = _make_ve_project(tmp_path)
        bin_dir = _make_ve_stub(tmp_path)

        result = _run_adapter(plugin_root, project, bin_dir)

        assert json.loads(result.stdout)["additional_context"]

    def test_cursor_plugin_root_env_takes_precedence(self, tmp_path):
        """When Cursor supplies CURSOR_PLUGIN_ROOT, it wins over the $0 walk:
        point it at a second root whose manifest carries a different version
        and observe that version in the drift warning."""
        run_root = _make_plugin_root(tmp_path)
        other = tmp_path / "other"
        other_root = _make_plugin_root(other, version="8.8.8")
        project = _make_ve_project(tmp_path)
        bin_dir = _make_ve_stub(tmp_path, version="0.1.0")

        result = _run_adapter(
            run_root,
            project,
            bin_dir,
            extra_env={"CURSOR_PLUGIN_ROOT": str(other_root)},
        )

        assert "8.8.8" in json.loads(result.stdout)["additional_context"]


class TestManifestFallback:
    """A Cursor-only install may lack .claude-plugin/plugin.json; the shared
    core falls back to .cursor-plugin/plugin.json (same version, DEC-014)."""

    def test_cursor_only_manifest_still_yields_version(self, tmp_path):
        plugin_root = _make_plugin_root(
            tmp_path, version="9.9.9", claude_manifest=False
        )
        project = _make_ve_project(tmp_path)
        bin_dir = _make_ve_stub(tmp_path, version="0.1.0")

        result = _run_adapter(plugin_root, project, bin_dir)

        context = json.loads(result.stdout)["additional_context"]
        assert "9.9.9" in context, "version must come from the Cursor manifest"

    def test_claude_manifest_wins_when_both_exist(self, tmp_path):
        """The fallback must not invert precedence for the normal layout."""
        plugin_root = _make_plugin_root(tmp_path, version="9.9.9")
        cursor_manifest = plugin_root / ".cursor-plugin" / "plugin.json"
        cursor_manifest.write_text(
            json.dumps({"name": "vibe-engineer", "version": "7.7.7"})
        )
        project = _make_ve_project(tmp_path)
        bin_dir = _make_ve_stub(tmp_path, version="0.1.0")

        result = _run_adapter(plugin_root, project, bin_dir)

        context = json.loads(result.stdout)["additional_context"]
        assert "9.9.9" in context
        assert "7.7.7" not in context


class TestRegistration:
    """The chain Cursor follows: manifest -> hooks config -> script."""

    def test_adapter_script_is_executable(self):
        assert ADAPTER_SCRIPT.exists()
        assert os.access(ADAPTER_SCRIPT, os.X_OK)

    def test_hooks_config_registers_session_start_adapter(self):
        config = json.loads(CURSOR_HOOKS_CONFIG.read_text())
        assert config.get("version") == 1
        commands = [
            hook["command"] for hook in config["hooks"]["sessionStart"]
        ]
        assert any(
            ".cursor-plugin/hooks/session_start.sh" in command
            for command in commands
        ), "sessionStart must run the Cursor adapter, not the Claude core"
        assert not any(
            command.rstrip().endswith("/hooks/session_start.sh")
            and ".cursor-plugin" not in command
            for command in commands
        ), "the plain-text Claude core must never be registered directly"

    def test_registered_events_are_cursor_events(self):
        """Claude Code capitalizes its event names (SessionStart); Cursor's
        are camelCase (sessionStart). Shipping the wrong casing fails
        silently — the hook simply never fires."""
        config = json.loads(CURSOR_HOOKS_CONFIG.read_text())
        # Verified against cursor.com/docs/hooks.md (fetched 2026-08-14).
        cursor_events = {
            "sessionStart", "sessionEnd", "preToolUse", "postToolUse",
            "postToolUseFailure", "subagentStart", "subagentStop",
            "beforeShellExecution", "afterShellExecution",
            "beforeMCPExecution", "afterMCPExecution", "beforeReadFile",
            "afterFileEdit", "beforeSubmitPrompt", "preCompact", "stop",
            "afterAgentResponse", "afterAgentThought", "beforeTabFileRead",
            "afterTabFileEdit", "workspaceOpen",
        }
        unknown = set(config["hooks"]) - cursor_events
        assert not unknown, f"not Cursor hook events: {sorted(unknown)}"
