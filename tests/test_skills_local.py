"""Tests for opt-in project-local skill reification (DEC-015, as amended).

# Chunk: docs/chunks/plugin_local_skills - Opt-in project-local skill reification

The plugin remains the default distribution channel; these tests pin the
opt-in alternative's contract: render from the single template source into
the standard .agents/skills/ layout, maintain the .claude/skills
compatibility symlink (never replacing a real directory ve does not own),
migrate the legacy .claude/skills/ render, own only what you rendered,
refuse what you don't own, and surface version drift without failing
anyone's gate.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest
from click.testing import CliRunner

from cli import cli
from integrity import IntegrityValidator
from plugin_render import SKILLS_KIND, templates_for_flavor
from skills_local import (
    LOCAL_MARKER_PREFIX,
    load_manifest,
    local_skills_status,
    reify_local_skills,
)

FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _skill_templates() -> list[str]:
    return [
        t for t in templates_for_flavor("claude")
        if pathlib.PurePosixPath(t).parts[0] == SKILLS_KIND
    ]


@pytest.fixture
def project(tmp_path):
    """A minimal consuming project (not the plugin source repo).

    A subdirectory rather than tmp_path itself, so tests can place other
    state (a fake HOME) beside the project without it counting as inside.
    """
    root = tmp_path / "proj"
    (root / "docs" / "trunk").mkdir(parents=True)
    return root


class TestReify:
    def test_renders_every_claude_skill_template(self, project):
        result = reify_local_skills(project, "9.9.9")

        assert len(result.written) == len(_skill_templates())
        assert result.refused == []
        for path in result.written:
            assert path.name == "SKILL.md"
            assert path.is_relative_to(project / ".agents" / "skills")

    def test_marker_sits_after_intact_frontmatter(self, project):
        result = reify_local_skills(project, "9.9.9")

        for path in result.written:
            text = path.read_text()
            match = FRONTMATTER_RE.match(text)
            assert match, f"{path} lost its frontmatter"
            after = text[match.end():]
            assert after.startswith(LOCAL_MARKER_PREFIX)
            assert "ve skills reify" in after.splitlines()[0]

    def test_manifest_records_ownership_and_version(self, project):
        reify_local_skills(project, "9.9.9")

        manifest = load_manifest(project)
        assert manifest is not None
        assert manifest["ve_version"] == "9.9.9"
        expected = sorted(
            pathlib.PurePosixPath(t).name.removesuffix(".jinja2").removesuffix(".md")
            for t in _skill_templates()
        )
        assert manifest["owned"] == expected
        # The manifest lives in the standard directory.
        assert (project / ".agents" / "skills" / ".ve-local-skills.json").is_file()

    def test_second_run_is_idempotent(self, project):
        first = reify_local_skills(project, "9.9.9")
        contents = {p: p.read_text() for p in first.written}

        second = reify_local_skills(project, "9.9.9")

        assert {p: p.read_text() for p in second.written} == contents
        assert second.refused == []
        assert second.warnings == []

    def test_version_bump_rerenders_owned_files(self, project):
        reify_local_skills(project, "9.9.9")
        result = reify_local_skills(project, "10.0.0")

        assert result.refused == []
        sample = result.written[0].read_text()
        assert "ve 10.0.0" in sample.splitlines()[len(FRONTMATTER_RE.match(sample).group().splitlines())]
        assert load_manifest(project)["ve_version"] == "10.0.0"

    def test_unowned_collision_refused_by_name_others_written(self, project):
        hand_made = project / ".agents" / "skills" / "ve-status"
        hand_made.mkdir(parents=True)
        (hand_made / "SKILL.md").write_text("---\nname: ve-status\n---\nmine\n")

        result = reify_local_skills(project, "9.9.9")

        assert result.refused == ["ve-status"]
        assert (hand_made / "SKILL.md").read_text().endswith("mine\n")
        assert len(result.written) == len(_skill_templates()) - 1
        assert "ve-status" not in load_manifest(project)["owned"]

    def test_refuses_the_plugin_source_repo(self, tmp_path):
        (tmp_path / ".claude-plugin").mkdir()
        (tmp_path / ".claude-plugin" / "plugin.json").write_text("{}")

        with pytest.raises(ValueError, match="plugin source repository"):
            reify_local_skills(tmp_path, "9.9.9")

    def test_writes_nothing_outside_target_skills_dir(self, project, tmp_path, monkeypatch):
        """Canary: writes are confined to .agents/skills plus the one symlink."""
        home = tmp_path / "home"
        cache = home / ".claude" / "plugins" / "cache" / "m" / "p" / "1.0"
        cache.mkdir(parents=True)
        (cache / "canary.txt").write_text("untouched")
        (home / ".claude" / "skills").mkdir(parents=True)
        monkeypatch.setenv("HOME", str(home))

        reify_local_skills(project, "9.9.9")

        assert (cache / "canary.txt").read_text() == "untouched"
        assert list((home / ".claude" / "skills").iterdir()) == []
        outside = [
            p for p in project.rglob("*")
            if p.is_file()
            and not p.is_relative_to(project / ".agents" / "skills")
            # rglob traverses the symlink into .agents/skills; a file whose
            # resolved location is inside the target dir is not "outside".
            and not p.resolve().is_relative_to((project / ".agents" / "skills").resolve())
        ]
        assert outside == []
        links = [p for p in project.rglob("*") if p.is_symlink()]
        assert links == [project / ".claude" / "skills"]


class TestCompatibilitySymlink:
    def test_symlink_created_relative_and_pointing_at_agents_skills(self, project):
        result = reify_local_skills(project, "9.9.9")

        link = project / ".claude" / "skills"
        assert result.symlink == link
        assert link.is_symlink()
        # Relative, mirroring the pre-DEC-010 _init_skills convention.
        assert not pathlib.Path(link.readlink()).is_absolute()
        assert link.resolve() == (project / ".agents" / "skills").resolve()
        # Claude Code sees the rendered skills through the link.
        assert (link / "chunk-create" / "SKILL.md").is_file()
        # .claude/ itself is a plain directory, not a symlink.
        assert (project / ".claude").is_dir()
        assert not (project / ".claude").is_symlink()

    def test_symlink_idempotent_across_reruns(self, project):
        reify_local_skills(project, "9.9.9")
        link = project / ".claude" / "skills"
        before = link.readlink()

        result = reify_local_skills(project, "9.9.9")

        assert link.is_symlink()
        assert link.readlink() == before
        assert result.warnings == []

    def test_real_unowned_claude_skills_left_untouched_no_symlink(self, project):
        hand_made = project / ".claude" / "skills" / "my-skill"
        hand_made.mkdir(parents=True)
        (hand_made / "SKILL.md").write_text("mine\n")

        result = reify_local_skills(project, "9.9.9")

        # Renders still land in the standard directory.
        assert len(result.written) == len(_skill_templates())
        # The hand-made directory is untouched and no symlink was placed.
        assert not (project / ".claude" / "skills").is_symlink()
        assert (hand_made / "SKILL.md").read_text() == "mine\n"
        assert list((project / ".claude" / "skills").iterdir()) == [hand_made]
        assert len(result.warnings) == 1
        assert "not managed by ve" in result.warnings[0]
        assert "Claude Code will not see" in result.warnings[0]


class TestLegacyMigration:
    def _legacy_render(self, project, version="0.0.9"):
        """Produce the 0.6.0/0.7.0 layout: a real .claude/skills/ with our
        manifest, by reifying into .agents/skills and moving the results."""
        reify_local_skills(project, version)
        agents = project / ".agents" / "skills"
        legacy = project / ".claude" / "skills"
        legacy.unlink()  # remove the symlink the current code created
        agents.rename(legacy)
        (project / ".agents").rmdir()
        return legacy

    def test_migrates_owned_content_and_manifest_then_symlinks(self, project):
        legacy = self._legacy_render(project)
        owned_before = load_manifest(project)["owned"]

        result = reify_local_skills(project, "9.9.9")

        assert sorted(result.migrated) == owned_before
        # Ownership survived the move: nothing refused, everything re-rendered.
        assert result.refused == []
        assert len(result.written) == len(_skill_templates())
        manifest = load_manifest(project)
        assert manifest["owned"] == owned_before
        assert manifest["ve_version"] == "9.9.9"
        assert (project / ".agents" / "skills" / ".ve-local-skills.json").is_file()
        # The legacy directory became the compatibility symlink.
        assert legacy.is_symlink()
        assert legacy.resolve() == (project / ".agents" / "skills").resolve()

    def test_legacy_dir_with_handmade_entry_keeps_dir_and_skips_symlink(self, project):
        legacy = self._legacy_render(project)
        hand_made = legacy / "my-skill"
        hand_made.mkdir()
        (hand_made / "SKILL.md").write_text("mine\n")

        result = reify_local_skills(project, "9.9.9")

        # ve-owned content moved; the hand-made skill stayed where it was.
        assert not legacy.is_symlink()
        assert list(legacy.iterdir()) == [hand_made]
        assert (hand_made / "SKILL.md").read_text() == "mine\n"
        assert len(result.written) == len(_skill_templates())
        assert any("Claude Code will not see" in w for w in result.warnings)

    def test_legacy_manifest_still_read_before_migration(self, project):
        """load_manifest falls back to .claude/skills/ so status and the
        validator see a 0.6.0/0.7.0 render before it is re-reified."""
        self._legacy_render(project, version="0.0.9")

        st = local_skills_status(project, "9.9.9")
        assert st.opted_in is True
        assert st.rendered_version == "0.0.9"
        assert st.drifted is True


class TestStatus:
    def test_not_opted_in(self, project):
        st = local_skills_status(project, "9.9.9")
        assert st.opted_in is False
        assert st.drifted is False

    def test_reports_drift_on_version_mismatch(self, project):
        reify_local_skills(project, "9.9.9")

        assert local_skills_status(project, "9.9.9").drifted is False
        assert local_skills_status(project, "10.0.0").drifted is True


class TestValidatorWarning:
    def _warnings(self, project):
        result = IntegrityValidator(project).validate()
        return [w for w in result.warnings if w.link_type == "skills→stale"]

    def _make_ve_project(self, project):
        for sub in ("chunks", "narratives", "investigations", "subsystems"):
            (project / "docs" / sub).mkdir(parents=True, exist_ok=True)

    def test_silent_when_not_opted_in(self, project):
        self._make_ve_project(project)
        assert self._warnings(project) == []

    def test_silent_when_versions_match(self, project):
        self._make_ve_project(project)
        from importlib.metadata import version
        reify_local_skills(project, version("vibe-engineer"))
        assert self._warnings(project) == []

    def test_warns_when_rendered_by_older_ve(self, project):
        self._make_ve_project(project)
        reify_local_skills(project, "0.0.1")

        warnings = self._warnings(project)
        assert len(warnings) == 1
        assert "ve skills reify" in warnings[0].message
        # A warning must not fail validation.
        assert IntegrityValidator(project).validate().success is True

    def test_warns_for_legacy_layout_manifest(self, project):
        """A 0.6.0/0.7.0 render (manifest still in .claude/skills/) gets the
        stale warning before anyone re-reifies and migrates."""
        self._make_ve_project(project)
        skills_dir = project / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / ".ve-local-skills.json").write_text(
            json.dumps({"schema": 1, "ve_version": "0.0.1", "owned": []})
        )

        warnings = self._warnings(project)
        assert len(warnings) == 1
        assert "ve skills reify" in warnings[0].message

    def test_corrupt_manifest_does_not_crash_validation(self, project):
        self._make_ve_project(project)
        skills_dir = project / ".agents" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / ".ve-local-skills.json").write_text("{not json")

        assert self._warnings(project) == []

    def test_corrupt_legacy_manifest_does_not_crash_validation(self, project):
        self._make_ve_project(project)
        skills_dir = project / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / ".ve-local-skills.json").write_text("{not json")

        assert self._warnings(project) == []


class TestCli:
    def test_reify_prints_paths_and_platform_notes(self, project):
        runner = CliRunner()
        result = runner.invoke(cli, ["skills", "reify", "--project-dir", str(project)])

        assert result.exit_code == 0, result.output
        assert "Wrote" in result.output
        assert "Symlink" in result.output
        assert "next session start" in result.output
        assert "agentskills.io" in result.output
        assert "Cursor" in result.output
        assert "plugin remains the default" in result.output

    def test_reify_exit_2_on_refusal(self, project):
        hand_made = project / ".agents" / "skills" / "ve-status"
        hand_made.mkdir(parents=True)
        (hand_made / "SKILL.md").write_text("mine\n")
        runner = CliRunner()

        result = runner.invoke(cli, ["skills", "reify", "--project-dir", str(project)])

        assert result.exit_code == 2
        assert "Refused ve-status" in result.output

    def test_reify_warns_on_unowned_claude_skills_dir(self, project):
        (project / ".claude" / "skills" / "my-skill").mkdir(parents=True)
        runner = CliRunner()

        result = runner.invoke(cli, ["skills", "reify", "--project-dir", str(project)])

        assert result.exit_code == 0, result.output
        assert "Warning" in result.output
        assert "Claude Code will not see" in result.output

    def test_status_reports_drift(self, project):
        reify_local_skills(project, "0.0.1")
        runner = CliRunner()

        result = runner.invoke(cli, ["skills", "status", "--project-dir", str(project)])

        assert result.exit_code == 0
        assert "Drift" in result.output
        assert "ve skills reify" in result.output
