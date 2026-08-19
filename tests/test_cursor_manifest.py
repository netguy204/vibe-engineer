"""Tests for the Cursor plugin scaffold.

Verifies the install contract a Cursor user depends on: manifests that
validate against the *actual* cursor/plugins schemas (vendored under
tests/fixtures/cursor_plugin_schemas/, see its PROVENANCE.md), that agree
with each other, and — the part that is easy to get wrong — that steer
Cursor's folder-based component discovery away from this repository's
Claude-flavored build product.

Cursor discovers components by folder when the manifest does not name
explicit paths: skills/, agents/, commands/, rules/, hooks/hooks.json,
mcp.json at the plugin root. This repository's root already holds skills/
(39 Claude-flavored SKILL.md files carrying `!`-backtick probes and
allowed-tools), agents/, and hooks/hooks.json (Claude's SessionStart
schema). A silent manifest would hand all of that to Cursor. The manifest
therefore declares skills, agents, and hooks explicitly, and
TestDiscoveryCollision is what keeps a future "simplification" from
deleting those declarations.

# Chunk: docs/chunks/dualplugin_cursor_scaffold - Cursor plugin scaffold
"""

import json
import re
from pathlib import Path

import jsonschema
import plugin_render
import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
CURSOR_DIR = REPO_ROOT / ".cursor-plugin"
PLUGIN_MANIFEST = CURSOR_DIR / "plugin.json"
MARKETPLACE_MANIFEST = CURSOR_DIR / "marketplace.json"

SCHEMA_DIR = Path(__file__).parent / "fixtures" / "cursor_plugin_schemas"

# Skills and agents rendered for Cursor, derived from the renderer rather
# than frozen here: dualplugin_cursor_render widened the Cursor flavor to the
# full surface, so these span every skill and both agents, and any template
# added later joins the checks automatically.
# Chunk: docs/chunks/dualplugin_cursor_render - Full-surface Cursor render
CURSOR_SKILLS = tuple(
    Path(name).stem.removesuffix(".md")
    for name in plugin_render.templates_for_flavor("cursor")
    if name.startswith("skills/")
)

CURSOR_AGENTS = tuple(
    Path(name).stem.removesuffix(".md")
    for name in plugin_render.templates_for_flavor("cursor")
    if name.startswith("agents/")
)

# Component types Cursor discovers by folder, and the default location it
# looks in. Any of these that the manifest does not explicitly declare must
# not exist at the repo root, or Cursor picks it up uninvited.
CURSOR_DEFAULT_LOCATIONS = {
    "skills": "skills",
    "agents": "agents",
    "commands": "commands",
    "rules": "rules",
    "hooks": "hooks/hooks.json",
    "mcpServers": "mcp.json",
}

# Component types whose Cursor default-discovery folder exists at this repo's
# root holding Claude-flavored content. Each maps to the manifest key that
# must override discovery for it.
COLLIDING_COMPONENTS = {
    "skills": "skills",
    "agents": "agents",
    "hooks": "hooks",
}


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text()
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, f"{path} has no YAML frontmatter block"
    return yaml.safe_load(match.group(1))


def _validate(instance: dict, schema_name: str) -> None:
    schema = _load_json(SCHEMA_DIR / schema_name)
    jsonschema.Draft7Validator.check_schema(schema)
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    assert not errors, "\n".join(
        f"{'/'.join(str(p) for p in e.path) or '/'}: {e.message}" for e in errors
    )


def _declared_paths(manifest: dict, key: str) -> list[str]:
    """Normalize a string-or-array manifest component field to a list."""
    value = manifest.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    return []


class TestPluginManifest:
    def test_validates_against_upstream_schema(self):
        """GOAL success criterion: the manifest validates against the current
        cursor/plugins spec. Checked against the vendored schema itself, not a
        paraphrase — the schema sets additionalProperties: false, so this also
        catches invented keys."""
        _validate(_load_json(PLUGIN_MANIFEST), "plugin.schema.json")

    def test_name_matches_the_claude_plugin_name(self):
        """One plugin, two ecosystems: a user who installs `vibe-engineer` in
        either editor should be installing the same thing under the same name."""
        cursor = _load_json(PLUGIN_MANIFEST)
        claude = _load_json(REPO_ROOT / ".claude-plugin" / "plugin.json")
        assert cursor["name"] == claude["name"]

    def test_author_is_an_object(self):
        """The live schema types `author` as an object with a required `name`
        (additionalProperties: false). A bare string — the shape the chunk's
        June 2026 notes implied — is a hard validation failure."""
        author = _load_json(PLUGIN_MANIFEST)["author"]
        assert isinstance(author, dict)
        assert author["name"]

    def test_description_is_present_and_substantive(self):
        """Submission checklist: `description` clearly explains the purpose."""
        description = _load_json(PLUGIN_MANIFEST)["description"]
        assert len(description) > 30


class TestMarketplaceManifest:
    def test_validates_against_upstream_schema(self):
        _validate(_load_json(MARKETPLACE_MANIFEST), "marketplace.schema.json")

    def test_entry_name_matches_plugin_manifest(self):
        """Upstream's own validator (scripts/validate-plugins.mjs) fails the
        build when these disagree; so do we."""
        plugin = _load_json(PLUGIN_MANIFEST)
        marketplace = _load_json(MARKETPLACE_MANIFEST)
        assert len(marketplace["plugins"]) == 1
        assert marketplace["plugins"][0]["name"] == plugin["name"]

    def test_source_resolves_to_repo_root(self):
        """Cursor resolves a marketplace entry's source against the marketplace
        root (the directory holding .cursor-plugin/) and then looks for
        <source>/.cursor-plugin/plugin.json."""
        entry = _load_json(MARKETPLACE_MANIFEST)["plugins"][0]
        marketplace_root = MARKETPLACE_MANIFEST.parent.parent
        source_dir = (marketplace_root / entry["source"]).resolve()
        assert source_dir == REPO_ROOT.resolve()
        assert (source_dir / ".cursor-plugin" / "plugin.json").is_file()


class TestDiscoveryCollision:
    """The manifest must never let Cursor fall through to Claude content.

    Deleting any one of these declarations is a silent regression: the plugin
    still installs, and Cursor users get skills full of literal `!`-backtick
    lines and a hooks file whose event names it does not recognize.
    """

    @pytest.mark.parametrize("component", sorted(COLLIDING_COMPONENTS))
    def test_colliding_default_folder_holds_claude_content(self, component):
        """Guards the premise. If Claude's build product ever moves out of the
        repo root, this test fails and the overrides below can be revisited
        rather than cargo-culted."""
        folder = COLLIDING_COMPONENTS[component]
        assert (REPO_ROOT / folder).exists(), (
            f"{folder}/ no longer exists at the repo root; the collision this "
            "manifest guards against may no longer be real"
        )

    @pytest.mark.parametrize("component", sorted(COLLIDING_COMPONENTS))
    def test_manifest_declares_component_explicitly(self, component):
        manifest = _load_json(PLUGIN_MANIFEST)
        assert component in manifest, (
            f"{component!r} is absent from .cursor-plugin/plugin.json, so "
            f"Cursor falls back to folder discovery and picks up the "
            f"Claude-flavored {COLLIDING_COMPONENTS[component]}/ at the repo "
            "root"
        )

    @pytest.mark.parametrize("component", ["skills", "agents"])
    def test_declared_path_is_not_the_claude_tree(self, component):
        manifest = _load_json(PLUGIN_MANIFEST)
        claude_tree = (REPO_ROOT / COLLIDING_COMPONENTS[component]).resolve()
        declared = _declared_paths(manifest, component)
        assert declared, f"{component} must name at least one path"
        for raw in declared:
            resolved = (REPO_ROOT / raw).resolve()
            assert resolved != claude_tree, (
                f"{component} points at the Claude build product {raw}"
            )
            assert CURSOR_DIR.resolve() in resolved.parents or resolved == (
                CURSOR_DIR.resolve()
            ), f"{component} path {raw} is outside the Cursor render tree"

    # Chunk: docs/chunks/dualplugin_lifecycle_release - hooks declaration
    # points at the Cursor sessionStart config instead of the pre-hook empty
    # placeholder. The declaration is still doing DEC-014's discovery-override
    # job: it is what keeps Cursor away from the root hooks/hooks.json, whose
    # event names (SessionStart) Cursor does not recognize.
    def test_hooks_declares_the_cursor_hooks_config(self):
        hooks = _load_json(PLUGIN_MANIFEST)["hooks"]
        assert isinstance(hooks, str), (
            "hooks must be a path to the Cursor hooks config; an inline "
            "object was the pre-dualplugin_lifecycle_release placeholder"
        )
        resolved = (REPO_ROOT / hooks).resolve()
        claude_hooks = (REPO_ROOT / COLLIDING_COMPONENTS["hooks"]).resolve()
        assert CURSOR_DIR.resolve() in resolved.parents, (
            f"hooks config {hooks} lives outside the Cursor render tree"
        )
        assert resolved != (claude_hooks / "hooks.json").resolve(), (
            "hooks points at the Claude hooks config"
        )
        assert resolved.is_file(), f"hooks declares {hooks}, which does not exist"

    def test_declared_hooks_config_registers_session_start(self):
        """The config the manifest names must actually declare sessionStart
        running an existing, executable script — a declared-but-empty config
        would silently drop the session-lifecycle story for Cursor users."""
        hooks_path = REPO_ROOT / _load_json(PLUGIN_MANIFEST)["hooks"]
        config = _load_json(hooks_path)
        session_start = config["hooks"]["sessionStart"]
        assert session_start, "sessionStart must register at least one hook"
        for entry in session_start:
            command = entry["command"]
            # The command names the adapter via ${CURSOR_PLUGIN_ROOT}, which
            # resolves to the repo root at install time.
            relative = command.replace("${CURSOR_PLUGIN_ROOT}/", "")
            script = REPO_ROOT / relative
            assert script.is_file(), f"sessionStart command {command} not found"
            assert script.stat().st_mode & 0o111, f"{relative} is not executable"

    @pytest.mark.parametrize("component", sorted(CURSOR_DEFAULT_LOCATIONS))
    def test_undeclared_component_has_no_default_location(self, component):
        """Forward guard for the collisions that do not exist yet.

        Today only skills/, agents/, and hooks/hooks.json exist at the repo
        root. If someone later adds commands/, rules/, or mcp.json for the
        Claude side, Cursor would start discovering them the moment they
        appear — with no error and no test failure anywhere else. Either
        declare the component in the Cursor manifest or do not create its
        default location.
        """
        if component in _load_json(PLUGIN_MANIFEST):
            return
        default = REPO_ROOT / CURSOR_DEFAULT_LOCATIONS[component]
        assert not default.exists(), (
            f"{default.relative_to(REPO_ROOT)} exists but the Cursor manifest "
            f"does not declare {component!r}, so Cursor will discover it. "
            "Add an explicit path (or an empty inline config) to "
            ".cursor-plugin/plugin.json."
        )

    @pytest.mark.parametrize("component", ["skills", "agents"])
    def test_declared_path_exists(self, component):
        """A declared path that does not exist is worse than no declaration:
        the override is what keeps Cursor away from the Claude tree, so it has
        to be a real directory even before anything renders into it."""
        for raw in _declared_paths(_load_json(PLUGIN_MANIFEST), component):
            assert (REPO_ROOT / raw).is_dir(), (
                f"{component} declares {raw}, which does not exist"
            )

    def test_declared_agents_dir_holds_only_rendered_agents(self):
        """Cursor loads every .md/.mdc/.markdown file here as an agent, so
        the directory must hold exactly the rendered agents — a stray README
        or scratch file would ship as an agent nobody declared.

        # Chunk: docs/chunks/dualplugin_cursor_render - Cursor agent renders
        """
        agents_dir = REPO_ROOT / _declared_paths(_load_json(PLUGIN_MANIFEST), "agents")[0]
        loadable = sorted(
            p.name
            for p in agents_dir.iterdir()
            if p.suffix in {".md", ".mdc", ".markdown"}
        )
        assert loadable == sorted(f"{name}.md" for name in CURSOR_AGENTS), (
            f"{agents_dir} must hold exactly the rendered agents; found "
            f"{loadable}"
        )

    @pytest.mark.parametrize("component", ["skills", "agents", "hooks"])
    def test_declared_paths_are_relative_and_contained(self, component):
        """Submission checklist: all manifest paths are relative and valid —
        no `..`, no absolute paths."""
        for raw in _declared_paths(_load_json(PLUGIN_MANIFEST), component):
            assert not raw.startswith("/"), f"{raw} is absolute"
            assert ".." not in Path(raw).parts, f"{raw} escapes the plugin root"


class TestCursorSkillRenders:
    """Every skill as Cursor will actually read it.

    Parameterized over the full Cursor surface (39 skills, derived from the
    renderer) since dualplugin_cursor_render deleted the two-skill pilot
    boundary.
    """

    def _skill(self, name: str) -> Path:
        declared = _declared_paths(_load_json(PLUGIN_MANIFEST), "skills")[0]
        return REPO_ROOT / declared / name / "SKILL.md"

    @pytest.mark.parametrize("name", CURSOR_SKILLS)
    def test_skill_exists_at_the_declared_path(self, name):
        """Rendering somewhere the manifest does not point is the same as not
        rendering at all."""
        assert self._skill(name).is_file(), (
            f"{name} missing under the manifest's declared skills path; run "
            "`uv run ve plugin render --flavor cursor`"
        )

    @pytest.mark.parametrize("name", CURSOR_SKILLS)
    def test_frontmatter_matches_cursor_skill_format(self, name):
        frontmatter = _parse_frontmatter(self._skill(name))
        assert frontmatter["name"] == name
        assert frontmatter["description"]
        assert "allowed-tools" not in frontmatter, (
            "allowed-tools is a Claude-only frontmatter field"
        )

    @pytest.mark.parametrize("name", CURSOR_SKILLS)
    def test_no_claude_only_idioms(self, name):
        """Cursor has no `!`-backtick preprocessing: a probe written that way
        reaches the model as literal text instead of command output."""
        body = self._skill(name).read_text()
        offenders = re.findall(r"^\s*[-*].*!`", body, re.MULTILINE)
        assert not offenders, (
            f"{name} carries Claude `!`-backtick probe lines: {offenders}"
        )
        assert "allowed-tools:" not in body
        assert "CLAUDE_PLUGIN_ROOT" not in body
        assert "CLAUDE_PROJECT_DIR" not in body
        assert "$ARGUMENTS" not in body, (
            "$ARGUMENTS is a Claude slash-command placeholder; nothing "
            "substitutes it in Cursor, so it would ship as dead text"
        )

    @pytest.mark.parametrize("name", CURSOR_SKILLS)
    def test_probe_commands_survive_the_flavor_change(self, name):
        """Dropping `!` must not drop the probe: the same command still has to
        reach the agent, as an instruction to run."""
        body = self._skill(name).read_text()
        assert "ve --help" in body

    @pytest.mark.parametrize("name", CURSOR_SKILLS)
    def test_no_unrendered_jinja_residue(self, name):
        body = self._skill(name).read_text()
        for token in ("{{", "{%", "{#"):
            assert token not in body, f"{name} contains unrendered Jinja2 {token}"


class TestCursorAgentRenders:
    """Both agents as Cursor will load them (subagents).

    # Chunk: docs/chunks/dualplugin_cursor_render - Cursor agent renders
    """

    def _agent(self, name: str) -> Path:
        declared = _declared_paths(_load_json(PLUGIN_MANIFEST), "agents")[0]
        return REPO_ROOT / declared / f"{name}.md"

    def test_both_agents_render(self):
        """The Cursor surface carries the same two agents as the Claude one."""
        assert sorted(CURSOR_AGENTS) == ["chunk-executor", "intent-auditor"]

    @pytest.mark.parametrize("name", CURSOR_AGENTS)
    def test_agent_exists_at_the_declared_path(self, name):
        assert self._agent(name).is_file(), (
            f"{name} missing under the manifest's declared agents path; run "
            "`uv run ve plugin render --flavor cursor`"
        )

    @pytest.mark.parametrize("name", CURSOR_AGENTS)
    def test_frontmatter_matches_cursor_agent_format(self, name):
        """Cursor's agent frontmatter is name + description (reference docs,
        Agent frontmatter fields). Claude's `tools` list has no Cursor
        counterpart and must not leak into this flavor."""
        frontmatter = _parse_frontmatter(self._agent(name))
        assert frontmatter["name"] == name
        assert frontmatter["description"]
        assert "tools" not in frontmatter, (
            "tools is Claude-only agent frontmatter"
        )
        assert "allowed-tools" not in frontmatter

    @pytest.mark.parametrize("name", CURSOR_AGENTS)
    def test_no_claude_only_idioms(self, name):
        body = self._agent(name).read_text()
        offenders = re.findall(r"^\s*[-*].*!`", body, re.MULTILINE)
        assert not offenders, (
            f"{name} carries Claude `!`-backtick probe lines: {offenders}"
        )
        assert "allowed-tools:" not in body
        assert "CLAUDE_PLUGIN_ROOT" not in body
        assert "CLAUDE_PROJECT_DIR" not in body
        assert "$ARGUMENTS" not in body

    @pytest.mark.parametrize("name", CURSOR_AGENTS)
    def test_carries_generated_marker(self, name):
        body = self._agent(name).read_text()
        assert plugin_render.GENERATED_MARKER_PREFIX in body
        assert f"src/templates/plugin/agents/{name}.md.jinja2" in body

    @pytest.mark.parametrize("name", CURSOR_AGENTS)
    def test_no_unrendered_jinja_residue(self, name):
        body = self._agent(name).read_text()
        for token in ("{{", "{%", "{#"):
            assert token not in body, f"{name} contains unrendered Jinja2 {token}"
