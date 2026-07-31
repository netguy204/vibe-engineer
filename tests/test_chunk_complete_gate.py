"""Tests for the `ve chunk complete` reference-existence gate.

# Chunk: docs/chunks/crossref_generator_verify - Completion gate tests

Success criterion: `ve chunk complete` refuses to transition a chunk to
ACTIVE when a declared code_references or code_paths entry names a
nonexistent target, leaving the status unchanged. Empty declarations still
complete at the CLI level (the emptiness gate stays in `ve chunk validate`).
"""

import pathlib

import pytest
from click.testing import CliRunner

from ve import cli


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def temp_project(tmp_path: pathlib.Path):
    """Set up a temporary project directory with a chunk to complete."""
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "docs" / "chunks").mkdir(parents=True)
    return project_dir


def _create_chunk(cli_runner, temp_project, name="my-chunk"):
    result = cli_runner.invoke(
        cli, ["chunk", "create", name, "--project-dir", str(temp_project)]
    )
    assert result.exit_code == 0
    return temp_project / "docs" / "chunks" / name


def _write_goal(
    chunk_path: pathlib.Path,
    code_paths: list[str] | None = None,
    code_references: list[dict] | None = None,
):
    """Overwrite GOAL.md with IMPLEMENTING status and the given declarations."""
    if code_paths:
        paths_yaml = "code_paths:\n" + "\n".join(f"- {p}" for p in code_paths)
    else:
        paths_yaml = "code_paths: []"

    if code_references:
        refs_lines = ["code_references:"]
        for ref in code_references:
            refs_lines.append(f"- ref: {ref['ref']}")
            refs_lines.append(f"  implements: \"{ref.get('implements', 'test')}\"")
        refs_yaml = "\n".join(refs_lines)
    else:
        refs_yaml = "code_references: []"

    (chunk_path / "GOAL.md").write_text(f"""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
{paths_yaml}
{refs_yaml}
---

# Chunk Goal

Test chunk content.
""")


def _chunk_status(chunk_path: pathlib.Path) -> str:
    for line in (chunk_path / "GOAL.md").read_text().splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("no status line found")


class TestCompleteReferenceGate:
    """`ve chunk complete` blocks on references naming nonexistent targets."""

    def test_completes_with_resolving_references(self, cli_runner, temp_project):
        """A chunk whose refs point at real files and symbols completes."""
        chunk_path = _create_chunk(cli_runner, temp_project)
        src = temp_project / "src"
        src.mkdir()
        (src / "widget.py").write_text("class Widget:\n    pass\n")
        _write_goal(
            chunk_path,
            code_paths=["src/widget.py"],
            code_references=[{"ref": "src/widget.py#Widget"}],
        )

        result = cli_runner.invoke(
            cli, ["chunk", "complete", "my-chunk", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert _chunk_status(chunk_path) == "ACTIVE"

    def test_blocks_on_missing_file(self, cli_runner, temp_project):
        """A ref naming a missing file blocks completion; status unchanged."""
        chunk_path = _create_chunk(cli_runner, temp_project)
        _write_goal(
            chunk_path,
            code_references=[{"ref": "src/ghost.py#Anything"}],
        )

        result = cli_runner.invoke(
            cli, ["chunk", "complete", "my-chunk", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "src/ghost.py" in result.output
        assert "Cannot complete" in result.output
        assert _chunk_status(chunk_path) == "IMPLEMENTING"

    def test_blocks_on_missing_symbol(self, cli_runner, temp_project):
        """A ref naming a missing symbol in a real file blocks completion."""
        chunk_path = _create_chunk(cli_runner, temp_project)
        src = temp_project / "src"
        src.mkdir()
        (src / "widget.py").write_text("class Widget:\n    pass\n")
        _write_goal(
            chunk_path,
            code_references=[{"ref": "src/widget.py#InventedWidget"}],
        )

        result = cli_runner.invoke(
            cli, ["chunk", "complete", "my-chunk", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "InventedWidget" in result.output
        assert _chunk_status(chunk_path) == "IMPLEMENTING"

    def test_blocks_on_missing_code_path(self, cli_runner, temp_project):
        """A code_paths entry naming a missing file blocks completion."""
        chunk_path = _create_chunk(cli_runner, temp_project)
        _write_goal(chunk_path, code_paths=["src/moved_away.py"])

        result = cli_runner.invoke(
            cli, ["chunk", "complete", "my-chunk", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "src/moved_away.py" in result.output
        assert _chunk_status(chunk_path) == "IMPLEMENTING"

    def test_directory_code_path_passes(self, cli_runner, temp_project):
        """A code_paths entry naming an existing directory completes."""
        chunk_path = _create_chunk(cli_runner, temp_project)
        (temp_project / "src" / "pkg").mkdir(parents=True)
        _write_goal(chunk_path, code_paths=["src/pkg"])

        result = cli_runner.invoke(
            cli, ["chunk", "complete", "my-chunk", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert _chunk_status(chunk_path) == "ACTIVE"

    def test_empty_declarations_still_complete(self, cli_runner, temp_project):
        """Empty code_paths and code_references pass the gate."""
        chunk_path = _create_chunk(cli_runner, temp_project)
        _write_goal(chunk_path)

        result = cli_runner.invoke(
            cli, ["chunk", "complete", "my-chunk", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert _chunk_status(chunk_path) == "ACTIVE"

    def test_gate_message_gives_guidance(self, cli_runner, temp_project):
        """The block message tells the agent what to do, not just what failed."""
        chunk_path = _create_chunk(cli_runner, temp_project)
        _write_goal(chunk_path, code_references=[{"ref": "src/ghost.py#Thing"}])

        result = cli_runner.invoke(
            cli, ["chunk", "complete", "my-chunk", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "Fix the reference or the code" in result.output


class TestTaskContextCompleteGate:
    """The task-context completion path applies the same gate."""

    def test_task_complete_blocks_on_missing_ref(self, cli_runner, tmp_path):
        """Completing an external chunk with a stale ref fails; status unchanged."""
        from conftest import setup_task_directory

        task_dir, external_path, _ = setup_task_directory(tmp_path)
        cli_runner.invoke(
            cli, ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        _write_goal(chunk_path, code_references=[{"ref": "src/ghost.py#Thing"}])

        result = cli_runner.invoke(
            cli, ["chunk", "complete", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "src/ghost.py" in result.output
        assert _chunk_status(chunk_path) == "IMPLEMENTING"

    def test_task_complete_passes_with_resolving_ref(self, cli_runner, tmp_path):
        """Completing an external chunk whose refs resolve succeeds."""
        from conftest import setup_task_directory

        task_dir, external_path, _ = setup_task_directory(tmp_path)
        cli_runner.invoke(
            cli, ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        src = external_path / "src"
        src.mkdir(exist_ok=True)
        (src / "widget.py").write_text("class Widget:\n    pass\n")
        _write_goal(chunk_path, code_references=[{"ref": "src/widget.py#Widget"}])

        result = cli_runner.invoke(
            cli, ["chunk", "complete", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0
        assert _chunk_status(chunk_path) == "ACTIVE"
