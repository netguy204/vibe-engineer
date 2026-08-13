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

import pytest
from click.testing import CliRunner

import plugin_render
from test_plugin_manifest import REPO_ROOT
from ve import cli

PILOT_TEMPLATES = [
    "skills/chunk-create.md.jinja2",
    "skills/ve-status.md.jinja2",
]


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
        assert len(skills) == 40, (
            f"expected all 40 skills in the collection, found {len(skills)}"
        )
        assert "agents/chunk-executor.md.jinja2" in agents
        assert "agents/intent-auditor.md.jinja2" in agents
        assert len(agents) == 2

    def test_partials_are_not_rendered(self):
        for name in _template_names():
            assert not name.startswith("partials/"), (
                f"{name}: partials are include/import material, not outputs"
            )

    def test_claude_idiom_partial_exists(self):
        partial = (
            plugin_render.plugin_collection_dir()
            / "partials"
            / "claude"
            / "idioms.md.jinja2"
        )
        assert partial.is_file(), (
            "the Claude idiom partial is the flavor-substitution point; "
            "dualplugin_cursor_scaffold adds partials/cursor/ alongside it"
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


class TestMarkerConvention:
    def test_marker_prefix_avoids_legacy_header_string(self):
        assert "AUTO-GENERATED" not in plugin_render.GENERATED_MARKER_PREFIX


class TestRenderCli:
    def _scratch_plugin_repo(self, root: pathlib.Path) -> None:
        manifest_dir = root / ".claude-plugin"
        manifest_dir.mkdir()
        (manifest_dir / "plugin.json").write_text(
            json.dumps({"name": "vibe-engineer", "version": "0.0.0"})
        )

    def test_refuses_outside_plugin_source_repo(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plugin", "render"])
            assert result.exit_code != 0
            assert ".claude-plugin/plugin.json" in result.output

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
        runner = CliRunner()
        with runner.isolated_filesystem() as tmp:
            self._scratch_plugin_repo(pathlib.Path(tmp))
            result = runner.invoke(cli, ["plugin", "render", "--flavor", "cursor"])
            assert result.exit_code != 0
