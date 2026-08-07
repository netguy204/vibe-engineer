"""Tests for the never-resolved signal on cross-repository pointers.

# Chunk: docs/chunks/external_never_resolved - Never-verified cross-repo pointer tests

A `repo:` pointer whose far side was never committed dangles from birth, and
until now nothing distinguished it from a healthy pointer that simply had not
been resolved recently. `last_resolved` records that somebody once read the
target successfully; its *absence* is the signal.

The check is deliberately local: VE still declines to say whether a cross-repo
target exists, because that needs network or cache state. "Nobody has ever
looked" is a fact about this file.
"""

from __future__ import annotations

import pathlib
from datetime import datetime, timezone

import pytest
import yaml
from pydantic import ValidationError

from external_refs import create_external_yaml, load_external_ref, stamp_resolved
from integrity import IntegrityValidator
from models import ArtifactType, ExternalArtifactRef


def _pointer(tmp_path: pathlib.Path, name: str = "storm_harvester") -> pathlib.Path:
    """A cross-repo chunk pointer in a minimal VE tree."""
    (tmp_path / "docs" / "trunk").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "chunks").mkdir(parents=True, exist_ok=True)
    create_external_yaml(
        project_path=tmp_path,
        short_name=name,
        external_repo_ref="org/other-repo",
        external_artifact_id=name,
        artifact_type=ArtifactType.CHUNK,
    )
    return tmp_path / "docs" / "chunks" / name


class TestModelField:
    def test_absent_by_default(self):
        ref = ExternalArtifactRef(
            artifact_type=ArtifactType.CHUNK, artifact_id="a", repo="org/repo"
        )
        assert ref.last_resolved is None

    def test_accepts_an_iso_instant(self):
        ref = ExternalArtifactRef(
            artifact_type=ArtifactType.CHUNK,
            artifact_id="a",
            repo="org/repo",
            last_resolved="2026-08-07T11:14:08+00:00",
        )
        assert ref.last_resolved == "2026-08-07T11:14:08+00:00"

    def test_rejects_a_non_instant(self):
        """A garbled value must not masquerade as a resolution that happened."""
        with pytest.raises(ValidationError, match="ISO-8601"):
            ExternalArtifactRef(
                artifact_type=ArtifactType.CHUNK,
                artifact_id="a",
                repo="org/repo",
                last_resolved="last tuesday",
            )

    def test_rejected_on_a_peer_pointer(self):
        """Peers resolve against the same commit, so they have nothing to stamp."""
        with pytest.raises(ValidationError, match="last_resolved.*invalid with 'tree'"):
            ExternalArtifactRef(
                artifact_type=ArtifactType.CHUNK,
                artifact_id="a",
                tree="pybusiness",
                last_resolved="2026-08-07T11:14:08+00:00",
            )


class TestStamping:
    def test_stamps_a_cross_repo_pointer(self, tmp_path):
        pointer = _pointer(tmp_path)
        assert load_external_ref(pointer).last_resolved is None

        assert stamp_resolved(pointer) is True
        assert load_external_ref(pointer).last_resolved is not None

    def test_preserves_every_other_field(self, tmp_path):
        pointer = _pointer(tmp_path)
        before = yaml.safe_load((pointer / "external.yaml").read_text())

        stamp_resolved(pointer)

        after = yaml.safe_load((pointer / "external.yaml").read_text())
        after.pop("last_resolved")
        assert after == before

    def test_replaces_rather_than_appends_on_a_second_resolve(self, tmp_path):
        pointer = _pointer(tmp_path)
        first = datetime(2026, 1, 1, tzinfo=timezone.utc)
        second = datetime(2026, 8, 7, tzinfo=timezone.utc)

        stamp_resolved(pointer, when=first)
        stamp_resolved(pointer, when=second)

        text = (pointer / "external.yaml").read_text()
        assert text.count("last_resolved:") == 1
        assert load_external_ref(pointer).last_resolved == second.isoformat()

    def test_declines_to_stamp_a_peer_pointer(self, tmp_path):
        pointer = _pointer(tmp_path)
        data = yaml.safe_load((pointer / "external.yaml").read_text())
        data.pop("repo")
        data.pop("track", None)
        data["tree"] = "pybusiness"
        (pointer / "external.yaml").write_text(yaml.dump(data))

        assert stamp_resolved(pointer) is False
        assert "last_resolved" not in (pointer / "external.yaml").read_text()


class TestValidatorSignal:
    def test_warns_for_a_pointer_nobody_has_ever_resolved(self, tmp_path):
        _pointer(tmp_path)

        result = IntegrityValidator(tmp_path).validate()

        never = [w for w in result.warnings if w.link_type == "external→never-resolved"]
        assert len(never) == 1
        assert "has never resolved" in never[0].message
        assert "ve external resolve storm_harvester" in never[0].message

    def test_the_finding_is_a_warning_so_validation_still_passes(self, tmp_path):
        """Every pointer is unverified until someone resolves it once."""
        _pointer(tmp_path)

        result = IntegrityValidator(tmp_path).validate()

        assert result.success is True
        assert not [
            e for e in result.errors if "never" in getattr(e, "message", "").lower()
        ]

    def test_silent_once_the_pointer_has_resolved(self, tmp_path):
        pointer = _pointer(tmp_path)
        stamp_resolved(pointer)

        result = IntegrityValidator(tmp_path).validate()

        assert not [
            w for w in result.warnings if w.link_type == "external→never-resolved"
        ]

    def test_silent_for_peer_pointers(self, tmp_path):
        """`ve workspace validate` already reports a bad peer as missing-target."""
        pointer = _pointer(tmp_path)
        data = yaml.safe_load((pointer / "external.yaml").read_text())
        data.pop("repo")
        data.pop("track", None)
        data["tree"] = "pybusiness"
        (pointer / "external.yaml").write_text(yaml.dump(data))

        result = IntegrityValidator(tmp_path).validate()

        assert not [
            w for w in result.warnings if w.link_type == "external→never-resolved"
        ]
