"""Tests for the 've subsystem validate' CLI command."""

import pathlib

from ve import cli


def _write_subsystem_overview(
    subsystem_path: pathlib.Path,
    status: str,
    chunks: list[dict] | None = None,
):
    """Helper to write OVERVIEW.md with frontmatter.

    Args:
        subsystem_path: Path to subsystem directory
        status: Subsystem status (DISCOVERING, DOCUMENTED, etc.)
        chunks: List of dicts with 'chunk_id' and 'relationship' keys
    """
    overview_path = subsystem_path / "OVERVIEW.md"

    if chunks:
        chunks_yaml = "chunks:\n"
        for chunk in chunks:
            chunks_yaml += f"  - chunk_id: {chunk['chunk_id']}\n"
            chunks_yaml += f"    relationship: {chunk['relationship']}\n"
    else:
        chunks_yaml = "chunks: []"

    frontmatter = f"""---
status: {status}
{chunks_yaml}
code_references: []
---

# Subsystem

Test subsystem content.
"""
    overview_path.write_text(frontmatter)


def _create_chunk(temp_project: pathlib.Path, chunk_name: str):
    """Helper to create a chunk directory with GOAL.md."""
    chunk_path = temp_project / "docs" / "chunks" / chunk_name
    chunk_path.mkdir(parents=True, exist_ok=True)
    (chunk_path / "GOAL.md").write_text("""---
status: IMPLEMENTING
code_references: []
---

# Chunk Goal
""")


class TestValidateCommandInterface:
    """Tests for 've subsystem validate' command interface."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["subsystem", "validate", "--help"])
        assert result.exit_code == 0
        assert "--project-dir" in result.output

    def test_subsystem_id_argument_required(self, runner, temp_project):
        """subsystem_id argument is required."""
        result = runner.invoke(
            cli,
            ["subsystem", "validate", "--project-dir", str(temp_project)]
        )
        # Should fail with missing argument error
        assert result.exit_code != 0

    def test_project_dir_option_works(self, runner, temp_project):
        """--project-dir option works correctly."""
        # Create subsystem with valid state
        subsystem_path = temp_project / "docs" / "subsystems" / "0001-validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(subsystem_path, "DOCUMENTED", [])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "0001-validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0


class TestValidSubsystem:
    """Tests for valid subsystem validation."""

    def test_valid_subsystem_passes(self, runner, temp_project):
        """Valid subsystem passes validation."""
        subsystem_path = temp_project / "docs" / "subsystems" / "0001-validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(subsystem_path, "DOCUMENTED", [])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "0001-validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "passed" in result.output.lower()

    def test_valid_subsystem_with_valid_chunk_ref_passes(self, runner, temp_project):
        """Subsystem with valid chunk reference passes validation."""
        # Create chunk first
        _create_chunk(temp_project, "0001-feature")

        # Create subsystem with reference to chunk
        subsystem_path = temp_project / "docs" / "subsystems" / "0001-validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(subsystem_path, "DOCUMENTED", [
            {"chunk_id": "0001-feature", "relationship": "implements"}
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "0001-validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0


class TestInvalidSubsystem:
    """Tests for invalid subsystem validation."""

    def test_nonexistent_subsystem_fails(self, runner, temp_project):
        """Non-existent subsystem fails with error."""
        result = runner.invoke(
            cli,
            ["subsystem", "validate", "9999-nonexistent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_invalid_chunk_ref_fails(self, runner, temp_project):
        """Subsystem with invalid chunk reference fails validation."""
        subsystem_path = temp_project / "docs" / "subsystems" / "0001-validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(subsystem_path, "DOCUMENTED", [
            {"chunk_id": "0001-nonexistent", "relationship": "implements"}
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "0001-validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "0001-nonexistent" in result.output

    def test_multiple_invalid_chunk_refs_reported(self, runner, temp_project):
        """Multiple invalid chunk references are all reported."""
        subsystem_path = temp_project / "docs" / "subsystems" / "0001-validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(subsystem_path, "DOCUMENTED", [
            {"chunk_id": "0001-nonexistent1", "relationship": "implements"},
            {"chunk_id": "0002-nonexistent2", "relationship": "uses"},
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "0001-validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        # Both errors should be reported
        assert "0001-nonexistent1" in result.output
        assert "0002-nonexistent2" in result.output
