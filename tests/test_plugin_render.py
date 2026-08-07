"""Tests for the build-time plugin template collection and `ve plugin render`.

The src/templates/plugin/ collection is the single source of truth for the
plugin command content it covers. Renders are committed; these tests keep the
committed renders in lockstep with the templates:

1. Drift test: for every template in the collection, a fresh render must be
   byte-identical to the committed output file. It fails when a template is
   edited without re-rendering, or when a committed render is hand-edited.
2. Marker convention: every rendered file carries a generated-from-template
   marker pointing at its own template, and the marker wording must never
   collide with the legacy "AUTO-GENERATED" header that
   src/project.py#_is_ve_generated_file keys on for legacy cleanup.
3. The `ve plugin render` CLI: renders the Claude flavor into skills/ and
   refuses to run outside the plugin source repo.

# Chunk: docs/chunks/dualplugin_template_source - Build-time plugin template collection
"""

import json
import pathlib
import re

import pytest
from click.testing import CliRunner

import plugin_render
from test_plugin_manifest import REPO_ROOT
from ve import cli

PILOT_TEMPLATES = [
    "skills/chunk-create.md.jinja2",
    "skills/ve-status.md.jinja2",
]

# Chunk: docs/chunks/dualplugin_cursor_scaffold - Cursor render target
CURSOR_TEMPLATES = list(plugin_render.FLAVOR_TEMPLATE_SUBSETS["cursor"])


def _template_names() -> list[str]:
    return plugin_render.list_plugin_templates()


class TestCollectionLayout:
    def test_pilot_templates_exist(self):
        """The two pilots prove the layer (dualplugin_template_source
        success criteria). dualplugin_content_migration extends this set."""
        names = _template_names()
        for pilot in PILOT_TEMPLATES:
            assert pilot in names

    def test_collection_covers_every_committed_render(self):
        """1:1 mapping between collection templates and committed renders,
        in both directions. A committed skills/*/SKILL.md or agents/*.md without
        a template would silently escape drift coverage (hand edits to it
        would survive); a template without a committed render is caught by
        the drift test itself, but is asserted here too for symmetry.

        # Chunk: docs/chunks/dualplugin_content_migration - Full-surface template coverage
        """
        templates = set(_template_names())
        committed = {
            f"skills/{path.parent.name}.md.jinja2"
            for path in (REPO_ROOT / "skills").glob("*/SKILL.md")
        } | {
            f"agents/{path.name}.jinja2"
            for path in (REPO_ROOT / "agents").glob("*.md")
        }
        missing_templates = committed - templates
        assert not missing_templates, (
            "committed renders without a source template (hand-added file?): "
            f"{sorted(missing_templates)}"
        )
        orphan_templates = templates - committed
        assert not orphan_templates, (
            "templates without a committed render — run `uv run ve plugin "
            f"render`: {sorted(orphan_templates)}"
        )

    def test_collection_spans_full_plugin_surface(self):
        """dualplugin_content_migration success criterion: every skill and both
        agents render from templates.

        The count is a snapshot of the current skill surface, not a cap — raise
        it when a skill is added, so long as the addition arrives as a template.
        """
        names = _template_names()
        skills = [n for n in names if n.startswith("skills/")]
        agents = [n for n in names if n.startswith("agents/")]
        assert len(skills) == 39, (
            f"expected all 39 skills in the collection, found {len(skills)}"
        )
        assert "agents/chunk-executor.md.jinja2" in agents
        assert "agents/intent-auditor.md.jinja2" in agents
        assert len(agents) == 2

    def test_partials_are_not_rendered(self):
        for name in _template_names():
            assert not name.startswith("partials/"), (
                f"{name}: partials are include/import material, not outputs"
            )

    @pytest.mark.parametrize("flavor", plugin_render.FLAVORS)
    def test_every_flavor_has_an_idiom_partial(self, flavor):
        """The idiom partial IS the flavor: templates import
        partials/<flavor>/idioms.md.jinja2 by name, so a flavor without one
        fails at render time rather than at declaration time."""
        partial = (
            plugin_render.plugin_collection_dir()
            / "partials"
            / flavor
            / "idioms.md.jinja2"
        )
        assert partial.is_file(), (
            f"{flavor} is declared in FLAVORS but has no idiom partial"
        )

    def test_flavors_implement_the_same_macro_interface(self):
        """A template body is flavor-blind: it calls a macro and the partial
        decides what that means. A macro present in one partial and missing
        from another is a render-time crash for whichever flavor lacks it.

        # Chunk: docs/chunks/dualplugin_cursor_scaffold - Idiom parity
        """
        partials = plugin_render.plugin_collection_dir() / "partials"
        macros = {}
        for flavor in plugin_render.FLAVORS:
            text = (partials / flavor / "idioms.md.jinja2").read_text()
            macros[flavor] = set(re.findall(r"{%-?\s*macro\s+(\w+)\s*\(", text))
        reference = macros[plugin_render.DEFAULT_FLAVOR]
        for flavor, names in macros.items():
            assert names == reference, (
                f"{flavor} idiom partial does not match the "
                f"{plugin_render.DEFAULT_FLAVOR} interface; "
                f"missing={sorted(reference - names)} "
                f"extra={sorted(names - reference)}"
            )


@pytest.mark.parametrize("template_name", _template_names() or PILOT_TEMPLATES)
class TestDrift:
    """Committed renders must match a fresh render byte-for-byte."""

    def test_committed_render_matches_fresh_render(self, template_name):
        committed = plugin_render.output_path(template_name, REPO_ROOT)
        assert committed.is_file(), (
            f"{template_name} has no committed render at {committed}; "
            "run `uv run ve plugin render`"
        )
        fresh = plugin_render.render_plugin_template(template_name)
        assert committed.read_text() == fresh, (
            f"{committed.relative_to(REPO_ROOT)} is out of sync with "
            f"src/templates/plugin/{template_name} — either the template was "
            "edited without re-rendering, or the committed render was edited "
            "directly. Run `uv run ve plugin render`."
        )

    def test_rendered_file_carries_generated_marker(self, template_name):
        fresh = plugin_render.render_plugin_template(template_name)
        assert plugin_render.GENERATED_MARKER_PREFIX in fresh
        assert f"src/templates/plugin/{template_name}" in fresh, (
            "the marker must point back at this file's own template"
        )

    def test_marker_does_not_collide_with_legacy_header(self, template_name):
        """src/project.py#_is_ve_generated_file deletes legacy init-rendered
        files by the 'AUTO-GENERATED' header; build-time renders must never
        match it (they are committed source, not per-project render output)."""
        fresh = plugin_render.render_plugin_template(template_name)
        assert "AUTO-GENERATED" not in fresh

    def test_render_ends_with_single_trailing_newline(self, template_name):
        fresh = plugin_render.render_plugin_template(template_name)
        assert fresh.endswith("\n")
        assert not fresh.endswith("\n\n")


@pytest.mark.parametrize("template_name", CURSOR_TEMPLATES)
class TestCursorDrift:
    """The Cursor flavor's committed renders, held to the same contract.

    # Chunk: docs/chunks/dualplugin_cursor_scaffold - Cursor render drift coverage
    """

    def test_committed_render_matches_fresh_render(self, template_name):
        committed = plugin_render.output_path(template_name, REPO_ROOT, "cursor")
        assert committed.is_file(), (
            f"{template_name} has no committed Cursor render at {committed}; "
            "run `uv run ve plugin render --flavor cursor`"
        )
        fresh = plugin_render.render_plugin_template(template_name, "cursor")
        assert committed.read_text() == fresh, (
            f"{committed.relative_to(REPO_ROOT)} is out of sync with "
            f"src/templates/plugin/{template_name} — run "
            "`uv run ve plugin render --flavor cursor`."
        )

    def test_render_lands_under_the_cursor_plugin_dir(self, template_name):
        """The two flavors must not write the same file. Claude Code requires
        content at the repo root, so Cursor's render is what moves."""
        cursor_out = plugin_render.output_path(template_name, REPO_ROOT, "cursor")
        claude_out = plugin_render.output_path(template_name, REPO_ROOT, "claude")
        assert cursor_out != claude_out
        assert (REPO_ROOT / ".cursor-plugin") in cursor_out.parents

    def test_flavors_differ(self, template_name):
        """If the Cursor render were byte-identical to the Claude one, the
        idiom substitution silently did nothing."""
        assert plugin_render.render_plugin_template(
            template_name, "cursor"
        ) != plugin_render.render_plugin_template(template_name, "claude")

    def test_carries_generated_marker(self, template_name):
        fresh = plugin_render.render_plugin_template(template_name, "cursor")
        assert plugin_render.GENERATED_MARKER_PREFIX in fresh
        assert f"src/templates/plugin/{template_name}" in fresh
        assert "AUTO-GENERATED" not in fresh


class TestCursorScope:
    """The Cursor pilot boundary is deliberate and should stay legible.

    # Chunk: docs/chunks/dualplugin_cursor_scaffold - Pilot scope boundary
    """

    def test_cursor_renders_only_the_pilot(self):
        selected = plugin_render.templates_for_flavor("cursor")
        assert sorted(selected) == sorted(CURSOR_TEMPLATES)
        assert len(selected) < len(plugin_render.templates_for_flavor("claude")), (
            "the Cursor subset should be a strict subset while the full "
            "surface is dualplugin_cursor_render's work"
        )

    def test_claude_renders_the_whole_collection(self):
        assert plugin_render.templates_for_flavor("claude") == (
            plugin_render.list_plugin_templates()
        )

    def test_subset_entries_name_real_templates(self):
        """A stale subset entry would silently render nothing."""
        known = set(plugin_render.list_plugin_templates())
        for flavor, subset in plugin_render.FLAVOR_TEMPLATE_SUBSETS.items():
            unknown = set(subset) - known
            assert not unknown, f"{flavor} subset names missing templates: {unknown}"


class TestMarkerConvention:
    def test_marker_prefix_avoids_legacy_header_string(self):
        assert "AUTO-GENERATED" not in plugin_render.GENERATED_MARKER_PREFIX


class TestRenderCli:
    def _scratch_plugin_repo(self, root: pathlib.Path, flavor: str = "claude") -> None:
        relpath = plugin_render.flavor_manifest_relpath(flavor)
        manifest = root.joinpath(*relpath.parts)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps({"name": "vibe-engineer", "version": "0.0.0"})
        )

    def test_refuses_outside_plugin_source_repo(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plugin", "render"])
            assert result.exit_code != 0
            assert ".claude-plugin/plugin.json" in result.output

    def test_cursor_flavor_refuses_without_the_cursor_manifest(self):
        """Each flavor guards on its own manifest. A repo that ships only the
        Claude plugin must not have a .cursor-plugin/ tree scaffolded into it.

        # Chunk: docs/chunks/dualplugin_cursor_scaffold - Per-flavor render guard
        """
        runner = CliRunner()
        with runner.isolated_filesystem() as tmp:
            self._scratch_plugin_repo(pathlib.Path(tmp), "claude")
            result = runner.invoke(cli, ["plugin", "render", "--flavor", "cursor"])
            assert result.exit_code != 0
            assert ".cursor-plugin/plugin.json" in result.output
            assert not (pathlib.Path(tmp) / ".cursor-plugin" / "skills").exists()

    def test_renders_cursor_flavor_into_cursor_plugin_dir(self):
        runner = CliRunner()
        with runner.isolated_filesystem() as tmp:
            root = pathlib.Path(tmp)
            self._scratch_plugin_repo(root, "cursor")
            result = runner.invoke(cli, ["plugin", "render", "--flavor", "cursor"])
            assert result.exit_code == 0, result.output
            for template_name in CURSOR_TEMPLATES:
                out = plugin_render.output_path(template_name, root, "cursor")
                assert out.is_file()
                assert out.read_text() == plugin_render.render_plugin_template(
                    template_name, "cursor"
                )
            # The pilot boundary: no Claude-flavored tree appears at the root.
            assert not (root / "skills").exists()

    def test_renders_collection_into_skills(self):
        runner = CliRunner()
        with runner.isolated_filesystem() as tmp:
            self._scratch_plugin_repo(pathlib.Path(tmp))
            result = runner.invoke(cli, ["plugin", "render"])
            assert result.exit_code == 0, result.output
            for template_name in PILOT_TEMPLATES:
                out = plugin_render.output_path(template_name, pathlib.Path(tmp))
                assert out.is_file()
                assert out.read_text() == plugin_render.render_plugin_template(
                    template_name
                )
                assert str(out.relative_to(tmp)) in result.output

    def test_render_is_idempotent(self):
        runner = CliRunner()
        with runner.isolated_filesystem() as tmp:
            self._scratch_plugin_repo(pathlib.Path(tmp))
            assert runner.invoke(cli, ["plugin", "render"]).exit_code == 0
            first = {
                name: plugin_render.output_path(name, pathlib.Path(tmp)).read_text()
                for name in _template_names()
            }
            assert runner.invoke(cli, ["plugin", "render"]).exit_code == 0
            for name, content in first.items():
                assert (
                    plugin_render.output_path(name, pathlib.Path(tmp)).read_text()
                    == content
                )

    def test_rejects_unknown_flavor(self):
        """A flavor with no idiom partial must be rejected at the CLI, not
        crash mid-render. "cursor" used to stand in for "unknown" here; it is
        a real flavor now, so this uses one that is genuinely absent."""
        assert "emacs" not in plugin_render.FLAVORS
        runner = CliRunner()
        with runner.isolated_filesystem() as tmp:
            self._scratch_plugin_repo(pathlib.Path(tmp))
            result = runner.invoke(cli, ["plugin", "render", "--flavor", "emacs"])
            assert result.exit_code != 0
