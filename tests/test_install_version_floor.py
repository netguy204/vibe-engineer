"""Rendered install and uvx lines name a minimum vibe-engineer version.

# Chunk: docs/chunks/template_install_version_floor - Minimum version in rendered install lines

The floor is computed from the rendering package's version, so these tests
compare rendered output against `install_version_floor()` and never hard-code
a release number.
"""

from __future__ import annotations

import pathlib
import re
from importlib.metadata import version as package_version

import pytest
from click.testing import CliRunner

import plugin_render
import template_system
from constants import template_dir
from skills_local import reify_local_skills
from template_system import (
    TemplateContext,
    install_version_floor,
    list_templates,
    render_template,
    version_floor,
)
from test_plugin_manifest import REPO_ROOT
from ve import cli

# An install or uvx line naming vibe-engineer, with any flags before the
# requirement. Groups: opening quote, version specifier (None when
# unpinned), closing quote.
INSTALL_LINE_RE = re.compile(
    r"(?:uvx\s+--from|uv\s+tool\s+install|pip\s+install)(?:\s+--\S+)*"
    r"\s+('?)vibe-engineer(>=[^'\s`]+)?('?)"
)
FLOORED_RE = re.compile(r"'vibe-engineer>=([^']+)'")
FLAVORS = sorted(plugin_render.FLAVOR_MANIFESTS)


def _reset_caches():
    install_version_floor.cache_clear()
    template_system._environments.clear()


def _all_renders() -> dict[str, str]:
    """Render every template in every collection, keyed by a readable label."""
    renders: dict[str, str] = {}
    for flavor in FLAVORS:
        for name in plugin_render.templates_for_flavor(flavor):
            renders[f"plugin[{flavor}]/{name}"] = plugin_render.render_plugin_template(
                name, flavor
            )
    for collection in sorted(p.name for p in template_dir.iterdir() if p.is_dir()):
        if collection == plugin_render.PLUGIN_COLLECTION:
            continue
        for name in list_templates(collection):
            renders[f"{collection}/{name}"] = render_template(
                collection, name, TemplateContext()
            )
    renders["claude/AGENTS.md.jinja2[workspace]"] = render_template(
        "claude", "AGENTS.md.jinja2", TemplateContext(in_workspace=True)
    )
    return renders


def _committed_renders() -> dict[str, str]:
    paths = [
        *(REPO_ROOT / "skills").glob("*/SKILL.md"),
        *(REPO_ROOT / "agents").glob("*.md"),
        *(REPO_ROOT / ".cursor-plugin").rglob("*.md"),
    ]
    return {str(p.relative_to(REPO_ROOT)): p.read_text() for p in paths}


def _unpinned(text: str) -> list[str]:
    return [m.group(0) for m in INSTALL_LINE_RE.finditer(text) if m.group(2) is None]


class TestVersionFloor:
    @pytest.mark.parametrize(
        ("version", "floor"),
        [
            ("0.9.0", "0.9.0"),
            ("0.9.0.post1", "0.9.0"),
            ("0.9.0-1", "0.9.0"),
            ("0.9.0+g1234", "0.9.0"),
            ("1!0.9.0", "0.9.0"),
            ("1.2", "1.2"),
            ("0.9.1.dev3+g471d0ad5", "0.9.0"),
            ("0.9.1.DEV3", "0.9.0"),
            ("0.10.0.dev1", "0.9.0"),
            ("0.10.0rc1", "0.9.0"),
            ("0.3.1.dev0", "0.3.0"),
            ("1.0.0a1", "0.0.0"),
            ("0.0.0.dev1", "0.0.0"),
        ],
    )
    def test_floor(self, version, floor):
        assert version_floor(version) == floor

    def test_rejects_unparseable_version(self):
        with pytest.raises(ValueError):
            version_floor("unknown")

    def test_install_floor_follows_installed_package(self):
        assert install_version_floor() == version_floor(package_version("vibe-engineer"))

    def test_environment_exposes_floor_as_global(self):
        env = template_system.get_environment("claude")
        assert env.globals["ve_version_floor"] == install_version_floor()


class TestDevBuild:
    @pytest.fixture
    def dev_version(self, monkeypatch):
        monkeypatch.setattr(
            template_system, "package_version", lambda _name: "0.9.1.dev3+g471d0ad5"
        )
        _reset_caches()
        yield
        monkeypatch.undo()
        _reset_caches()

    @pytest.mark.parametrize("flavor", FLAVORS)
    def test_dev_build_renders_last_release(self, dev_version, flavor):
        # The skill reaches the install line through an idiom macro import.
        rendered = plugin_render.render_plugin_template("skills/chunk-plan.md.jinja2", flavor)
        assert FLOORED_RE.findall(rendered) == ["0.9.0", "0.9.0"]

    def test_dev_build_reaches_agents_md(self, dev_version):
        rendered = render_template("claude", "AGENTS.md.jinja2", TemplateContext())
        assert set(FLOORED_RE.findall(rendered)) == {"0.9.0"}


class TestRenderedOutput:
    def test_no_unpinned_install_line_in_any_render(self):
        offenders = {
            label: hits for label, text in _all_renders().items() if (hits := _unpinned(text))
        }
        assert offenders == {}

    def test_no_unpinned_install_line_in_committed_renders(self):
        offenders = {
            label: hits
            for label, text in _committed_renders().items()
            if (hits := _unpinned(text))
        }
        assert offenders == {}

    def test_every_floor_matches_package_version(self):
        floors = {
            label: set(FLOORED_RE.findall(text)) for label, text in _all_renders().items()
        }
        assert {f for found in floors.values() for f in found} == {install_version_floor()}
        for label in (
            "claude/AGENTS.md.jinja2",
            "claude/AGENTS.md.jinja2[workspace]",
            "trunk/ARTIFACTS.md.jinja2",
            *(f"plugin[{fl}]/skills/ve-status.md.jinja2" for fl in FLAVORS),
            *(f"plugin[{fl}]/skills/chunk-commit.md.jinja2" for fl in FLAVORS),
        ):
            assert floors[label], label

    def test_requirement_is_shell_quoted(self):
        for text in _all_renders().values():
            for m in INSTALL_LINE_RE.finditer(text):
                assert (m.group(1), m.group(3)) == ("'", "'"), m.group(0)

    def test_uv_tool_install_upgrades(self):
        # A plain `uv tool install` leaves an older tool in place.
        for text in _all_renders().values():
            for m in re.finditer(r"uv tool install(?:\s+--\S+)*", text):
                assert "--upgrade" in m.group(0), m.group(0)


class TestRenderers:
    def test_skills_reify_carries_floor(self, tmp_path):
        project = tmp_path / "proj"
        (project / "docs" / "trunk").mkdir(parents=True)
        reify_local_skills(project, package_version("vibe-engineer"))
        text = (project / ".agents" / "skills" / "ve-status" / "SKILL.md").read_text()
        assert f"'vibe-engineer>={install_version_floor()}'" in text
        assert _unpinned(text) == []

    def test_ve_init_carries_floor(self, tmp_path):
        result = CliRunner().invoke(cli, ["init", "--project-dir", str(tmp_path)])
        assert result.exit_code == 0, result.output
        expected = f"'vibe-engineer>={install_version_floor()}'"
        for rel in ("AGENTS.md", "docs/trunk/ARTIFACTS.md"):
            text = (tmp_path / rel).read_text()
            assert expected in text, rel
            assert _unpinned(text) == [], rel

    @pytest.mark.parametrize("flavor", FLAVORS)
    def test_plugin_render_carries_floor(self, flavor, tmp_path):
        manifest = plugin_render.flavor_manifest_relpath(flavor)
        (tmp_path / pathlib.Path(*manifest.parts)).parent.mkdir(parents=True)
        (tmp_path / pathlib.Path(*manifest.parts)).write_text("{}")
        written = plugin_render.render_plugin_collection(tmp_path, flavor)
        status = next(p for p in written if p.parent.name == "ve-status")
        assert f"'vibe-engineer>={install_version_floor()}'" in status.read_text()
