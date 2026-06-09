"""Tests for the Claude Code plugin scaffold.

Verifies the install contract that `claude plugin marketplace add` and
`claude plugin install` depend on: valid manifests that agree with each
other, a read-only pilot command, and the canonical plugin layout.

# Chunk: docs/chunks/plugin_scaffold - Claude Code plugin scaffold
"""

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
PLUGIN_MANIFEST = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_MANIFEST = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PILOT_COMMAND = REPO_ROOT / "commands" / "ve-status.md"


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text()
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, f"{path} has no YAML frontmatter block"
    return yaml.safe_load(match.group(1))


class TestPluginManifest:
    def test_plugin_manifest_is_valid(self):
        manifest = _load_json(PLUGIN_MANIFEST)
        assert manifest["name"] == "vibe-engineer"
        assert manifest["version"], "plugin version must be non-empty"
        assert manifest["description"], "plugin description must be non-empty"
        assert manifest["author"], "plugin author must be non-empty"

    def test_plugin_name_is_kebab_case(self):
        manifest = _load_json(PLUGIN_MANIFEST)
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", manifest["name"])


class TestMarketplaceManifest:
    def test_marketplace_manifest_is_valid(self):
        manifest = _load_json(MARKETPLACE_MANIFEST)
        assert manifest["name"], "marketplace name must be non-empty"
        assert manifest["owner"], "marketplace owner must be non-empty"
        assert len(manifest["plugins"]) == 1

    def test_marketplace_entry_agrees_with_plugin_manifest(self):
        plugin = _load_json(PLUGIN_MANIFEST)
        marketplace = _load_json(MARKETPLACE_MANIFEST)
        entry = marketplace["plugins"][0]
        assert entry["name"] == plugin["name"]

    def test_marketplace_source_resolves_to_repo_root(self):
        marketplace = _load_json(MARKETPLACE_MANIFEST)
        entry = marketplace["plugins"][0]
        # Claude Code resolves relative sources against the marketplace
        # root: the directory containing .claude-plugin/.
        marketplace_root = MARKETPLACE_MANIFEST.parent.parent
        source_dir = (marketplace_root / entry["source"]).resolve()
        assert source_dir == REPO_ROOT.resolve()
        # The resolved plugin root must contain the plugin manifest.
        assert (source_dir / ".claude-plugin" / "plugin.json").is_file()


class TestPilotCommand:
    def test_pilot_command_exists_with_frontmatter(self):
        frontmatter = _parse_frontmatter(PILOT_COMMAND)
        assert frontmatter["name"] == "ve-status"
        assert frontmatter["description"], "pilot command needs a description"

    def test_pilot_command_is_read_only(self):
        """The pilot proves the install path; it must not mutate state."""
        frontmatter = _parse_frontmatter(PILOT_COMMAND)
        allowed = frontmatter["allowed-tools"]
        tools = [t.strip() for t in allowed.split(",")]
        for tool in tools:
            assert tool.startswith("Bash(ve "), (
                f"pilot command allows non-ve tool: {tool}"
            )
            # No write-capable ve invocations.
            assert not re.search(
                r"\bve (chunk (create|activate|demote|complete)|init|orch inject)",
                tool,
            ), f"pilot command allows a write-capable invocation: {tool}"

    def test_pilot_command_wraps_chunk_list(self):
        body = PILOT_COMMAND.read_text()
        assert "ve chunk list --current" in body


class TestPluginLayout:
    def test_content_directories_exist_at_plugin_root(self):
        for directory in ("commands", "skills", "agents", "hooks"):
            assert (REPO_ROOT / directory).is_dir(), (
                f"plugin content directory {directory}/ missing at repo root"
            )
