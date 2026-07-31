"""Tests for the 've subsystem validate' CLI command."""

import pathlib

from ve import cli


def _write_subsystem_overview(
    subsystem_path: pathlib.Path,
    status: str,
    chunks: list[dict] | None = None,
    code_references: list[dict] | None = None,
):
    """Helper to write OVERVIEW.md with frontmatter.

    Args:
        subsystem_path: Path to subsystem directory
        status: Subsystem status (DISCOVERING, DOCUMENTED, etc.)
        chunks: List of dicts with 'chunk_id' and 'relationship' keys
        code_references: List of dicts with 'ref' and 'implements' keys
    """
    overview_path = subsystem_path / "OVERVIEW.md"

    if chunks:
        chunks_yaml = "chunks:\n"
        for chunk in chunks:
            chunks_yaml += f"  - chunk_id: {chunk['chunk_id']}\n"
            chunks_yaml += f"    relationship: {chunk['relationship']}\n"
    else:
        chunks_yaml = "chunks: []"

    if code_references:
        refs_yaml = "code_references:\n"
        for ref in code_references:
            refs_yaml += f"  - ref: \"{ref['ref']}\"\n"
            refs_yaml += f"    implements: \"{ref.get('implements', 'test')}\"\n"
    else:
        refs_yaml = "code_references: []"

    frontmatter = f"""---
status: {status}
{chunks_yaml}
{refs_yaml}
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
        subsystem_path = temp_project / "docs" / "subsystems" / "validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(subsystem_path, "DOCUMENTED", [])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0


class TestValidSubsystem:
    """Tests for valid subsystem validation."""

    def test_valid_subsystem_passes(self, runner, temp_project):
        """Valid subsystem passes validation."""
        subsystem_path = temp_project / "docs" / "subsystems" / "validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(subsystem_path, "DOCUMENTED", [])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "passed" in result.output.lower()

    def test_valid_subsystem_with_valid_chunk_ref_passes(self, runner, temp_project):
        """Subsystem with valid chunk reference passes validation."""
        # Create chunk first
        _create_chunk(temp_project, "feature")

        # Create subsystem with reference to chunk
        subsystem_path = temp_project / "docs" / "subsystems" / "validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(subsystem_path, "DOCUMENTED", [
            {"chunk_id": "feature", "relationship": "implements"}
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0


class TestInvalidSubsystem:
    """Tests for invalid subsystem validation."""

    def test_nonexistent_subsystem_fails(self, runner, temp_project):
        """Non-existent subsystem fails with error."""
        result = runner.invoke(
            cli,
            ["subsystem", "validate", "nonexistent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_invalid_chunk_ref_fails(self, runner, temp_project):
        """Subsystem with invalid chunk reference fails validation."""
        subsystem_path = temp_project / "docs" / "subsystems" / "validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(subsystem_path, "DOCUMENTED", [
            {"chunk_id": "nonexistent", "relationship": "implements"}
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "nonexistent" in result.output

    def test_multiple_invalid_chunk_refs_reported(self, runner, temp_project):
        """Multiple invalid chunk references are all reported."""
        subsystem_path = temp_project / "docs" / "subsystems" / "validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(subsystem_path, "DOCUMENTED", [
            {"chunk_id": "nonexistent1", "relationship": "implements"},
            {"chunk_id": "nonexistent_two", "relationship": "uses"},
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        # Both errors should be reported
        assert "nonexistent1" in result.output
        assert "nonexistent_two" in result.output


# Chunk: docs/chunks/crossref_generator_verify - Subsystem code_references verification tests
class TestCodeReferenceValidation:
    """Tests for code_references existence checking in 've subsystem validate'.

    Success criterion: an invented symbol name (the OriginationSimulator
    class of defect) or a missing file fails validation loudly; verified
    refs and non-Python file refs pass.
    """

    def _make_subsystem(self, temp_project, code_references):
        subsystem_path = temp_project / "docs" / "subsystems" / "validation"
        subsystem_path.mkdir(parents=True)
        _write_subsystem_overview(
            subsystem_path, "DISCOVERING", [], code_references
        )
        return subsystem_path

    def test_ref_to_existing_symbol_passes(self, runner, temp_project):
        """A ref naming a real file and defined symbol passes."""
        src = temp_project / "src"
        src.mkdir(exist_ok=True)
        (src / "analyzer.py").write_text(
            "class OriginationRiskAnalyzer:\n    pass\n"
        )
        self._make_subsystem(temp_project, [
            {"ref": "src/analyzer.py#OriginationRiskAnalyzer",
             "implements": "risk analysis"},
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_invented_symbol_fails(self, runner, temp_project):
        """A plausible-but-nonexistent symbol in a real file fails validation."""
        src = temp_project / "src"
        src.mkdir(exist_ok=True)
        (src / "analyzer.py").write_text(
            "class OriginationRiskAnalyzer:\n    pass\n"
        )
        self._make_subsystem(temp_project, [
            {"ref": "src/analyzer.py#OriginationSimulator",
             "implements": "invented by the generator"},
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "OriginationSimulator" in result.output

    def test_missing_file_fails(self, runner, temp_project):
        """A ref naming a nonexistent file fails validation."""
        self._make_subsystem(temp_project, [
            {"ref": "src/ghost.py#Anything", "implements": "missing file"},
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "src/ghost.py" in result.output

    def test_file_only_ref_to_non_python_file_passes(self, runner, temp_project):
        """A file-only ref to an existing non-Python file passes."""
        (temp_project / "config.yaml").write_text("key: value\n")
        self._make_subsystem(temp_project, [
            {"ref": "config.yaml", "implements": "configuration"},
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_empty_code_references_passes(self, runner, temp_project):
        """A subsystem with no code_references still validates."""
        self._make_subsystem(temp_project, [])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_unparseable_python_warns_but_passes(self, runner, temp_project):
        """An unparseable Python target is uncheckable: surfaced, not fatal."""
        src = temp_project / "src"
        src.mkdir(exist_ok=True)
        (src / "broken.py").write_text("def broken(:\n")
        self._make_subsystem(temp_project, [
            {"ref": "src/broken.py#broken", "implements": "uncheckable"},
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "validate", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "src/broken.py" in result.output
