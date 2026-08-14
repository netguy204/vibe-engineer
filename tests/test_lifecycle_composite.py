"""COMPOSITE ownership through the completion path.

# Chunk: docs/chunks/lifecycle_composite_ownership - Six-status completion matrix

COMPOSITE shares ownership of live intent (CHUNKS.md); it must validate like
ACTIVE does, and `ve chunk complete` must never collapse it — or resurrect
SUPERSEDED/HISTORICAL — as a side effect of an unconditional status write.
"""

from __future__ import annotations

import pathlib
import re

import pytest
import yaml
from click.testing import CliRunner

from chunks import Chunks
from cli import cli
from models import COMPLETABLE_STATUSES, VALID_CHUNK_TRANSITIONS, ChunkStatus


def _write_chunk(root: pathlib.Path, name: str, status: str, ref_file: str = "src/mod.py") -> pathlib.Path:
    chunk_dir = root / "docs" / "chunks" / name
    chunk_dir.mkdir(parents=True)
    (chunk_dir / "GOAL.md").write_text(
        f"""---
status: {status}
code_paths: []
code_references:
- ref: {ref_file}#thing
  implements: what the thing is for
---
# Chunk Goal

Some intent.
"""
    )
    (chunk_dir / "PLAN.md").write_text("# Implementation Plan\n\nA real plan.\n")
    return chunk_dir


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    (root / "docs" / "trunk").mkdir(parents=True)
    (root / "docs" / "chunks").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "src" / "mod.py").write_text("def thing():\n    return 1\n")
    return root


def _status_on_disk(chunk_dir: pathlib.Path) -> str:
    match = re.match(r"^---\s*\n(.*?)\n---", (chunk_dir / "GOAL.md").read_text(), re.DOTALL)
    return yaml.safe_load(match.group(1))["status"]


class TestOwnershipPredicate:
    def test_matches_chunks_md_ownership_semantics(self):
        assert COMPLETABLE_STATUSES == {
            ChunkStatus.IMPLEMENTING,
            ChunkStatus.ACTIVE,
            ChunkStatus.COMPOSITE,
        }

    def test_only_historical_is_terminal(self):
        terminal = {s for s, targets in VALID_CHUNK_TRANSITIONS.items() if not targets}
        assert terminal == {ChunkStatus.HISTORICAL}


class TestValidateChunkComplete:
    @pytest.mark.parametrize("status", ["IMPLEMENTING", "ACTIVE", "COMPOSITE"])
    def test_completable_statuses_validate(self, project, status):
        _write_chunk(project, "subject", status)
        result = Chunks(project).validate_chunk_complete("subject")
        assert result.success, result.errors

    @pytest.mark.parametrize("status", ["FUTURE", "SUPERSEDED", "HISTORICAL"])
    def test_non_completable_statuses_fail_naming_the_status(self, project, status):
        _write_chunk(project, "subject", status)
        result = Chunks(project).validate_chunk_complete("subject")
        assert not result.success
        assert any(status in e for e in result.errors)

    def test_malformed_composite_fails_on_refs_not_status(self, project):
        """The whole point: a bad COMPOSITE fails for real reasons."""
        _write_chunk(project, "subject", "COMPOSITE", ref_file="src/gone.py")
        result = Chunks(project).validate_chunk_complete("subject")
        assert not result.success
        assert not any("COMPOSITE" in e for e in result.errors)
        assert any("gone.py" in e for e in result.errors)


class TestCompleteTransitions:
    def _complete(self, project, name, *extra):
        return CliRunner().invoke(
            cli, ["chunk", "complete", name, "--project-dir", str(project), *extra]
        )

    def test_implementing_completes(self, project):
        chunk_dir = _write_chunk(project, "subject", "IMPLEMENTING")
        result = self._complete(project, "subject")
        assert result.exit_code == 0, result.output
        assert _status_on_disk(chunk_dir) == "ACTIVE"

    def test_active_is_idempotent_no_op(self, project):
        chunk_dir = _write_chunk(project, "subject", "ACTIVE")
        result = self._complete(project, "subject")
        assert result.exit_code == 0
        assert "already ACTIVE" in result.output
        assert _status_on_disk(chunk_dir) == "ACTIVE"

    def test_composite_refused_without_force_nothing_written(self, project):
        chunk_dir = _write_chunk(project, "subject", "COMPOSITE")
        result = self._complete(project, "subject")
        assert result.exit_code == 1
        assert "co-owner" in result.output or "co-ownership" in result.output
        assert "--force" in result.output
        assert _status_on_disk(chunk_dir) == "COMPOSITE"

    def test_composite_with_force_collapses_to_active(self, project):
        chunk_dir = _write_chunk(project, "subject", "COMPOSITE")
        result = self._complete(project, "subject", "--force")
        assert result.exit_code == 0, result.output
        assert _status_on_disk(chunk_dir) == "ACTIVE"

    @pytest.mark.parametrize("status", ["SUPERSEDED", "HISTORICAL"])
    def test_illegal_transitions_refused_nothing_written(self, project, status):
        chunk_dir = _write_chunk(project, "subject", status)
        result = self._complete(project, "subject")
        assert result.exit_code == 1
        assert "not a valid transition" in result.output
        assert _status_on_disk(chunk_dir) == status

    @pytest.mark.parametrize("status", ["SUPERSEDED", "HISTORICAL"])
    def test_force_does_not_override_illegal_transitions(self, project, status):
        """--force forces exactly one thing: COMPOSITE -> ACTIVE."""
        chunk_dir = _write_chunk(project, "subject", status)
        result = self._complete(project, "subject", "--force")
        assert result.exit_code == 1
        assert _status_on_disk(chunk_dir) == status

    def test_missing_status_fails_closed_nothing_written(self, project):
        """Unreadable state refuses completion — whichever layer catches it,
        the contract is exit 1 and no write."""
        chunk_dir = _write_chunk(project, "subject", "IMPLEMENTING")
        goal = chunk_dir / "GOAL.md"
        goal.write_text(goal.read_text().replace("status: IMPLEMENTING\n", ""))
        result = self._complete(project, "subject")
        assert result.exit_code == 1
        assert "status:" not in (chunk_dir / "GOAL.md").read_text()

    def test_unknown_status_fails_closed_nothing_written(self, project):
        chunk_dir = _write_chunk(project, "subject", "MYSTERIOUS")
        result = self._complete(project, "subject")
        assert result.exit_code == 1
        assert _status_on_disk(chunk_dir) == "MYSTERIOUS"
