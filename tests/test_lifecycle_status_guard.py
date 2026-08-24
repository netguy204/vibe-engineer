"""Every chunk status write routes through the state machine.

# Chunk: docs/chunks/lifecycle_status_guard - 6x6 matrix derived from the map itself

`ve chunk status` may only traverse edges present in VALID_CHUNK_TRANSITIONS,
X -> X is an idempotent no-op, `--force` is the loud operator escape hatch,
and `ve chunk activate`'s FUTURE-only rule derives from the same map. The
matrix below is computed from VALID_CHUNK_TRANSITIONS at test time — a future
map change cannot drift these tests, only re-derive them.
"""

from __future__ import annotations

import itertools
import pathlib
import re

import pytest
import yaml
from click.testing import CliRunner

from cli import cli
from models import CHUNK_STATE_MACHINE, VALID_CHUNK_TRANSITIONS, ChunkStatus


def _write_chunk(root: pathlib.Path, name: str, status: str) -> pathlib.Path:
    chunk_dir = root / "docs" / "chunks" / name
    chunk_dir.mkdir(parents=True)
    (chunk_dir / "GOAL.md").write_text(
        f"""---
status: {status}
code_paths: []
code_references: []
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
    return root


def _status_on_disk(chunk_dir: pathlib.Path) -> str:
    match = re.match(
        r"^---\s*\n(.*?)\n---", (chunk_dir / "GOAL.md").read_text(), re.DOTALL
    )
    return yaml.safe_load(match.group(1))["status"]


def _goal_bytes(chunk_dir: pathlib.Path) -> bytes:
    return (chunk_dir / "GOAL.md").read_bytes()


def _set_status(project, name, target, *extra):
    return CliRunner().invoke(
        cli, ["chunk", "status", name, target, "--project-dir", str(project), *extra]
    )


# The full matrix, derived from the enum; legality judged against the map
# inside each test rather than hand-copied into parametrize data.
MATRIX = list(itertools.product(ChunkStatus, ChunkStatus))

ILLEGAL_EDGES = [
    (current, target)
    for current, target in MATRIX
    if current != target and target not in VALID_CHUNK_TRANSITIONS[current]
]

LEGAL_EDGES = [
    (current, target)
    for current, target in MATRIX
    if target in VALID_CHUNK_TRANSITIONS[current]
]


def _edge_id(pair):
    current, target = pair
    return f"{current.value}->{target.value}"


class TestStatusTransitionMatrix:
    """6x6: legal edges write, illegal edges refuse without writing, X -> X no-ops."""

    @pytest.mark.parametrize(
        "current,target", MATRIX, ids=[_edge_id(p) for p in MATRIX]
    )
    def test_matrix(self, project, current, target):
        chunk_dir = _write_chunk(project, "subject", current.value)
        before = _goal_bytes(chunk_dir)

        result = _set_status(project, "subject", target.value)

        if current == target:
            # Idempotent no-op: exit 0 and the file is byte-identical
            assert result.exit_code == 0, result.output
            assert _goal_bytes(chunk_dir) == before
        elif target in VALID_CHUNK_TRANSITIONS[current]:
            assert result.exit_code == 0, result.output
            assert _status_on_disk(chunk_dir) == target.value
        else:
            assert result.exit_code == 1
            # Refusal writes nothing — byte-identical, not merely same status
            assert _goal_bytes(chunk_dir) == before
            # The message names current status, requested status, and the
            # legal targets from the map
            assert current.value in result.output
            assert target.value in result.output
            for legal in VALID_CHUNK_TRANSITIONS[current]:
                assert legal.value in result.output

    def test_map_and_predicate_agree_everywhere(self):
        """The shared predicate is the map: violation is None exactly on map edges."""
        for current, target in MATRIX:
            violation = CHUNK_STATE_MACHINE.transition_violation(current, target)
            if target in VALID_CHUNK_TRANSITIONS[current]:
                assert violation is None
            else:
                assert violation is not None
                assert current.value in violation
                assert target.value in violation


class TestForceEscapeHatch:
    """--force traverses illegal edges loudly; it forces nothing else."""

    @pytest.mark.parametrize(
        "current,target", ILLEGAL_EDGES, ids=[_edge_id(p) for p in ILLEGAL_EDGES]
    )
    def test_force_performs_every_illegal_edge_with_warning(
        self, project, current, target
    ):
        chunk_dir = _write_chunk(project, "subject", current.value)
        result = _set_status(project, "subject", target.value, "--force")
        assert result.exit_code == 0, result.output
        assert _status_on_disk(chunk_dir) == target.value
        # The warning names the rule that was broken
        assert "Warning" in result.output
        assert f"Cannot transition from {current.value} to {target.value}" in result.output

    def test_force_on_legal_edge_is_a_no_op_flag(self, project):
        current, target = LEGAL_EDGES[0]
        chunk_dir = _write_chunk(project, "subject", current.value)
        result = _set_status(project, "subject", target.value, "--force")
        assert result.exit_code == 0, result.output
        assert _status_on_disk(chunk_dir) == target.value
        assert "Warning" not in result.output
        assert "forced" not in result.output

    def test_force_on_idempotent_no_op_writes_nothing(self, project):
        chunk_dir = _write_chunk(project, "subject", "ACTIVE")
        before = _goal_bytes(chunk_dir)
        result = _set_status(project, "subject", "ACTIVE", "--force")
        assert result.exit_code == 0, result.output
        assert _goal_bytes(chunk_dir) == before
        assert "Warning" not in result.output

    def test_force_cannot_write_a_status_that_does_not_exist(self, project):
        """--force overrides which edges may be traversed, never which values exist."""
        chunk_dir = _write_chunk(project, "subject", "ACTIVE")
        before = _goal_bytes(chunk_dir)
        result = _set_status(project, "subject", "MYSTERIOUS", "--force")
        assert result.exit_code == 1
        assert _goal_bytes(chunk_dir) == before
        assert "Invalid status" in result.output

    def test_typoed_on_disk_status_refused_without_force(self, project):
        """Unreadable current status fails closed: no write without --force."""
        chunk_dir = _write_chunk(project, "subject", "MYSTERIOUS")
        before = _goal_bytes(chunk_dir)
        result = _set_status(project, "subject", "ACTIVE")
        assert result.exit_code == 1
        assert _goal_bytes(chunk_dir) == before

    def test_typoed_on_disk_status_repaired_with_force(self, project):
        """The GOAL's named repair case: a typo'd status is fixed in tooling,
        loudly, instead of by hand-editing frontmatter."""
        chunk_dir = _write_chunk(project, "subject", "MYSTERIOUS")
        result = _set_status(project, "subject", "ACTIVE", "--force")
        assert result.exit_code == 0, result.output
        assert _status_on_disk(chunk_dir) == "ACTIVE"
        assert "Warning" in result.output

    def test_missing_status_key_refused_without_force(self, project):
        chunk_dir = _write_chunk(project, "subject", "IMPLEMENTING")
        goal = chunk_dir / "GOAL.md"
        goal.write_text(goal.read_text().replace("status: IMPLEMENTING\n", ""))
        before = _goal_bytes(chunk_dir)
        result = _set_status(project, "subject", "ACTIVE")
        assert result.exit_code == 1
        assert _goal_bytes(chunk_dir) == before

    def test_missing_status_key_repaired_with_force(self, project):
        chunk_dir = _write_chunk(project, "subject", "IMPLEMENTING")
        goal = chunk_dir / "GOAL.md"
        goal.write_text(goal.read_text().replace("status: IMPLEMENTING\n", ""))
        result = _set_status(project, "subject", "ACTIVE", "--force")
        assert result.exit_code == 0, result.output
        assert _status_on_disk(chunk_dir) == "ACTIVE"
        assert "Warning" in result.output


# Sources that cannot legally reach IMPLEMENTING, derived from the map
# (today: everything except FUTURE).
NON_ACTIVATABLE = [
    s
    for s in ChunkStatus
    if ChunkStatus.IMPLEMENTING not in VALID_CHUNK_TRANSITIONS[s]
]


class TestActivateGuard:
    """Activation is FUTURE -> IMPLEMENTING; refusals derive from the map."""

    def _activate(self, project, name):
        return CliRunner().invoke(
            cli, ["chunk", "activate", name, "--project-dir", str(project)]
        )

    def test_future_activates(self, project):
        chunk_dir = _write_chunk(project, "subject", "FUTURE")
        result = self._activate(project, "subject")
        assert result.exit_code == 0, result.output
        assert _status_on_disk(chunk_dir) == "IMPLEMENTING"

    @pytest.mark.parametrize(
        "status", NON_ACTIVATABLE, ids=[s.value for s in NON_ACTIVATABLE]
    )
    def test_non_future_sources_refused_naming_the_status(self, project, status):
        chunk_dir = _write_chunk(project, "subject", status.value)
        before = _goal_bytes(chunk_dir)
        result = self._activate(project, "subject")
        assert result.exit_code == 1
        assert _goal_bytes(chunk_dir) == before
        assert status.value in result.output
