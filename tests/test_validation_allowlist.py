"""Tests for the backreference allowlist.

The scanner is language-agnostic and so cannot tell a comment from a string
literal containing one. A project declares the paths where reference-shaped
text is not a reference; these tests hold that mechanism to two promises —
it suppresses what it claims, and it cannot rot unnoticed.

# Chunk: docs/chunks/validation_backref_allowlist - Allowlist behavior
"""

import pathlib

import pytest
import yaml

from integrity import IntegrityValidator
from template_system import IgnoredBackreferencePath, load_ve_config


def write_config(project_dir: pathlib.Path, entries: list[dict]) -> None:
    (project_dir / ".ve-config.yaml").write_text(
        yaml.safe_dump({"validation": {"ignore_backreferences": entries}})
    )


@pytest.fixture
def project(tmp_path):
    """A VE project with one real chunk and nothing else."""
    (tmp_path / "docs" / "trunk").mkdir(parents=True)
    (tmp_path / "docs" / "chunks" / "real_chunk").mkdir(parents=True)
    (tmp_path / "docs" / "chunks" / "real_chunk" / "GOAL.md").write_text(
        "---\nstatus: ACTIVE\ncode_paths: []\ncode_references: []\n---\n# Goal\n"
    )
    for sub in ("narratives", "investigations", "subsystems"):
        (tmp_path / "docs" / sub).mkdir(parents=True)
    return tmp_path


class TestParsing:
    def test_entry_requires_a_reason(self, project):
        write_config(project, [{"path": "tests/x.py"}])

        with pytest.raises(ValueError, match="non-empty 'reason'"):
            load_ve_config(project)

    def test_blank_reason_is_rejected(self, project):
        write_config(project, [{"path": "tests/x.py", "reason": "   "}])

        with pytest.raises(ValueError, match="non-empty 'reason'"):
            load_ve_config(project)

    def test_entry_requires_a_path(self, project):
        write_config(project, [{"reason": "because"}])

        with pytest.raises(ValueError, match="non-empty 'path'"):
            load_ve_config(project)

    def test_absent_config_yields_no_entries(self, project):
        assert load_ve_config(project).ignore_backreferences == ()


class TestGlobScope:
    """`*` must not cross a directory boundary — silent widening hides defects."""

    @pytest.mark.parametrize(
        "pattern,path,expected",
        [
            ("tests/a.py", "tests/a.py", True),
            ("tests/*.py", "tests/a.py", True),
            ("tests/*.py", "tests/sub/a.py", False),
            ("docs/investigations/*/prototypes/*.py", "docs/investigations/x/prototypes/y.py", True),
            ("docs/investigations/*/prototypes/*.py", "docs/investigations/x/y.py", False),
        ],
    )
    def test_match_scope(self, pattern, path, expected):
        entry = IgnoredBackreferencePath(path=pattern, reason="r")

        assert entry.matches(path) is expected


class TestSuppression:
    def _source_with_dangling_ref(self, project, name):
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Chunk: docs/chunks/does_not_exist - dangling\n")
        return path

    def test_findings_from_a_declared_path_are_dropped(self, project):
        self._source_with_dangling_ref(project, "fixtures/sample.py")
        write_config(project, [{"path": "fixtures/*.py", "reason": "fixture text"}])

        result = IntegrityValidator(project).validate()

        assert result.errors == []
        assert result.backrefs_suppressed == 1
        assert result.success

    def test_findings_elsewhere_still_fail(self, project):
        self._source_with_dangling_ref(project, "fixtures/sample.py")
        self._source_with_dangling_ref(project, "src/real.py")
        write_config(project, [{"path": "fixtures/*.py", "reason": "fixture text"}])

        result = IntegrityValidator(project).validate()

        assert [e.source for e in result.errors] == ["src/real.py:1"]
        assert not result.success

    def test_suppression_does_not_hide_a_nested_path(self, project):
        """The glob scope rule has teeth: nested files are still reported."""
        self._source_with_dangling_ref(project, "fixtures/deep/sample.py")
        write_config(project, [{"path": "fixtures/*.py", "reason": "fixture text"}])

        result = IntegrityValidator(project).validate()

        assert [e.source for e in result.errors] == ["fixtures/deep/sample.py:1"]


class TestStaleEntriesSurface:
    """An allowlist that cannot rot is the whole point of requiring reasons."""

    def test_entry_matching_nothing_is_reported(self, project):
        write_config(project, [{"path": "gone/*.py", "reason": "moved away"}])

        result = IntegrityValidator(project).validate()

        stale = [w for w in result.warnings if w.link_type == "allowlist→unused"]
        assert [w.target for w in stale] == ["gone/*.py"]
        assert "moved away" in stale[0].message

    def test_entry_matching_a_finding_free_file_is_reported(self, project):
        """Matching files is not enough — it must suppress something.

        A reference that merely resolves is not suppression: this file carries
        none at all, so the entry does no work and must say so.
        """
        clean = project / "fixtures" / "clean.py"
        clean.parent.mkdir(parents=True)
        clean.write_text("def f():\n    return 1\n")
        write_config(project, [{"path": "fixtures/*.py", "reason": "fixture text"}])

        result = IntegrityValidator(project).validate()

        stale = [w for w in result.warnings if w.link_type == "allowlist→unused"]
        assert [w.target for w in stale] == ["fixtures/*.py"]

    def test_entry_suppressing_only_a_warning_counts_as_used(self, project):
        """Suppressing a bidirectional warning is real work, not a no-op."""
        path = project / "fixtures" / "sample.py"
        path.parent.mkdir(parents=True)
        path.write_text("# Chunk: docs/chunks/real_chunk - resolves, but unlisted\n")
        write_config(project, [{"path": "fixtures/*.py", "reason": "fixture text"}])

        result = IntegrityValidator(project).validate()

        assert result.backrefs_suppressed == 1
        assert [w for w in result.warnings if w.link_type == "allowlist→unused"] == []

    def test_used_entry_is_not_reported(self, project):
        path = project / "fixtures" / "sample.py"
        path.parent.mkdir(parents=True)
        path.write_text("# Chunk: docs/chunks/does_not_exist - dangling\n")
        write_config(project, [{"path": "fixtures/*.py", "reason": "fixture text"}])

        result = IntegrityValidator(project).validate()

        assert [w for w in result.warnings if w.link_type == "allowlist→unused"] == []
