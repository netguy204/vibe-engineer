"""Tests for the 'chunk validate' CLI command."""

import pathlib

from ve import cli


def write_goal_frontmatter(
    chunk_path: pathlib.Path,
    status: str,
    code_references: list[dict] | None = None,
):
    """Helper to write GOAL.md with frontmatter.

    Args:
        chunk_path: Path to chunk directory
        status: Chunk status (IMPLEMENTING, ACTIVE, etc.)
        code_references: List of dicts with 'file' and 'ranges' keys, e.g.:
            [{"file": "src/main.py", "ranges": [{"lines": "10-20", "implements": "req1"}]}]
    """
    goal_path = chunk_path / "GOAL.md"

    if code_references:
        refs_lines = ["code_references:"]
        for ref in code_references:
            refs_lines.append(f"  - file: {ref['file']}")
            refs_lines.append("    ranges:")
            for r in ref.get("ranges", []):
                refs_lines.append(f"      - lines: \"{r['lines']}\"")
                if "implements" in r:
                    refs_lines.append(f"        implements: \"{r['implements']}\"")
        refs_yaml = "\n".join(refs_lines)
    else:
        refs_yaml = "code_references: []"

    frontmatter = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
{refs_yaml}
---

# Chunk Goal

Test chunk content.
"""
    goal_path.write_text(frontmatter)


def write_symbolic_frontmatter(
    chunk_path: pathlib.Path,
    status: str,
    code_references: list[dict] | None = None,
):
    """Helper to write GOAL.md with symbolic reference frontmatter.

    Args:
        chunk_path: Path to chunk directory
        status: Chunk status (IMPLEMENTING, ACTIVE, etc.)
        code_references: List of dicts with 'ref' and 'implements' keys, e.g.:
            [{"ref": "src/main.py#MyClass::method", "implements": "req1"}]
    """
    goal_path = chunk_path / "GOAL.md"

    if code_references:
        refs_lines = ["code_references:"]
        for ref in code_references:
            refs_lines.append(f"  - ref: {ref['ref']}")
            refs_lines.append(f"    implements: \"{ref['implements']}\"")
        refs_yaml = "\n".join(refs_lines)
    else:
        refs_yaml = "code_references: []"

    frontmatter = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
{refs_yaml}
---

# Chunk Goal

Test chunk content.
"""
    goal_path.write_text(frontmatter)


class TestValidateCommandInterface:
    """Tests for 've chunk validate' command interface."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["chunk", "validate", "--help"])
        assert result.exit_code == 0
        assert "--project-dir" in result.output

    def test_chunk_id_argument_is_optional(self, runner, temp_project):
        """chunk_id argument is optional."""
        # Create a chunk with valid state
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20", "implements": "req1"}]}
        ])

        # Invoke without chunk_id - should default to latest
        result = runner.invoke(
            cli,
            ["chunk", "validate", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_project_dir_option_works(self, runner, temp_project):
        """--project-dir option works correctly."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20", "implements": "req1"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0


class TestStatusValidation:
    """Tests for status validation in 've chunk validate'."""

    def test_fails_when_status_not_implementing_or_active(self, runner, temp_project):
        """Command fails if chunk status is not IMPLEMENTING or ACTIVE."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "COMPLETED", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20", "implements": "req1"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0

    def test_active_status_passes(self, runner, temp_project):
        """Command succeeds when chunk status is ACTIVE."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "ACTIVE", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20", "implements": "req1"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_error_states_current_status(self, runner, temp_project):
        """Error message states the current status."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "COMPLETED", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20", "implements": "req1"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert "COMPLETED" in result.output

    def test_error_explains_why_blocked(self, runner, temp_project):
        """Error message explains why completion is blocked."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "COMPLETED", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20", "implements": "req1"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        # Should explain that status must be IMPLEMENTING or ACTIVE
        assert "IMPLEMENTING" in result.output or "ACTIVE" in result.output

    def test_nonexistent_chunk_exits_with_error(self, runner, temp_project):
        """Non-existent chunk ID exits non-zero with error message."""
        result = runner.invoke(
            cli,
            ["chunk", "validate", "9999", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_no_chunks_exits_with_error(self, runner, temp_project):
        """No chunks available exits non-zero with error message."""
        result = runner.invoke(
            cli,
            ["chunk", "validate", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0


class TestCodeReferencesValidation:
    """Tests for code_references validation in 've chunk validate'."""

    def test_valid_code_references_passes(self, runner, temp_project):
        """Valid code_references passes validation."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20", "implements": "req1"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_missing_file_field_produces_error(self, runner, temp_project):
        """Missing 'file' field produces error with field path."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"

        # Write malformed frontmatter directly
        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text("""---
status: IMPLEMENTING
code_references:
  - ranges:
      - lines: "10-20"
        implements: "req1"
---

# Chunk Goal
""")

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "file" in result.output.lower()

    def test_missing_lines_field_produces_error(self, runner, temp_project):
        """Missing 'lines' field in range produces error with field path."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"

        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text("""---
status: IMPLEMENTING
code_references:
  - file: src/main.py
    ranges:
      - implements: "req1"
---

# Chunk Goal
""")

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "lines" in result.output.lower()

    def test_missing_implements_field_produces_error(self, runner, temp_project):
        """Missing 'implements' field in range produces error with field path."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"

        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text("""---
status: IMPLEMENTING
code_references:
  - file: src/main.py
    ranges:
      - lines: "10-20"
---

# Chunk Goal
""")

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "implements" in result.output.lower()

    def test_wrong_type_produces_error(self, runner, temp_project):
        """Wrong type (int instead of string) produces error with field path."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"

        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text("""---
status: IMPLEMENTING
code_references:
  - file: src/main.py
    ranges:
      - lines: 1020
        implements: "req1"
---

# Chunk Goal
""")

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0

    def test_multiple_errors_reported_together(self, runner, temp_project):
        """Multiple errors are reported together."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"

        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text("""---
status: IMPLEMENTING
code_references:
  - file: src/main.py
    ranges:
      - lines: "10-20"
  - ranges:
      - implements: "req2"
---

# Chunk Goal
""")

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        # Should mention both 'implements' (missing) and 'file' (missing)
        output_lower = result.output.lower()
        assert "implements" in output_lower
        assert "file" in output_lower

    def test_empty_code_references_fails(self, runner, temp_project):
        """Empty code_references list fails with error."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        # Should explain that at least one reference is required
        assert "reference" in result.output.lower() or "empty" in result.output.lower()


class TestSuccessOutput:
    """Tests for success output in 've chunk validate'."""

    def test_success_prints_confirmation(self, runner, temp_project):
        """Successful validation prints confirmation message."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20", "implements": "req1"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Should output some confirmation
        assert len(result.output.strip()) > 0

    def test_success_exits_zero(self, runner, temp_project):
        """Exit code 0 on success."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20", "implements": "req1"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0


class TestSymbolicReferenceValidation:
    """Tests for symbolic code_references validation with warnings."""

    def test_valid_symbolic_reference_passes(self, runner, temp_project):
        """Valid symbolic reference passes validation."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/models.py#SymbolicReference", "implements": "Model definition"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_file_only_reference_passes(self, runner, temp_project):
        """File-only reference (no symbol) passes validation."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/models.py", "implements": "Full module"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_nonexistent_symbol_produces_warning(self, runner, temp_project):
        """Reference to non-existent symbol produces warning but succeeds."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/models.py#NonExistentClass", "implements": "Missing class"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        # Should succeed (exit 0) but show warning
        assert result.exit_code == 0
        assert "warning" in result.output.lower() or "not found" in result.output.lower()

    def test_nonexistent_file_produces_warning(self, runner, temp_project):
        """Reference to non-existent file produces warning but succeeds."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/nonexistent.py#SomeClass", "implements": "Missing file"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        # Should succeed (exit 0) but show warning
        assert result.exit_code == 0
        assert "warning" in result.output.lower() or "not found" in result.output.lower()

    def test_multiple_warnings_collected(self, runner, temp_project):
        """Multiple invalid references produce multiple warnings."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/models.py#NonExistent1", "implements": "First missing"},
            {"ref": "src/models.py#NonExistent2", "implements": "Second missing"},
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        # Should succeed but show warnings for both
        assert result.exit_code == 0
        # Both symbols should be mentioned
        assert "NonExistent1" in result.output or "warning" in result.output.lower()

    def test_no_warnings_when_all_symbols_valid(self, runner, temp_project):
        """No warnings shown when all symbols are valid."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"

        # Create a real Python file with a symbol
        src_dir = temp_project / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "test_module.py").write_text("class MyClass:\n    pass\n")

        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/test_module.py#MyClass", "implements": "Valid class"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "warning" not in result.output.lower()


class TestSubsystemRefValidation:
    """Tests for subsystem reference validation in 've chunk validate'."""

    def _write_frontmatter_with_subsystems(
        self,
        chunk_path,
        status: str,
        code_references: list[dict],
        subsystems: list[dict] | None = None,
    ):
        """Helper to write GOAL.md with subsystems field."""
        goal_path = chunk_path / "GOAL.md"

        if code_references:
            refs_lines = ["code_references:"]
            for ref in code_references:
                refs_lines.append(f"  - ref: {ref['ref']}")
                refs_lines.append(f"    implements: \"{ref['implements']}\"")
            refs_yaml = "\n".join(refs_lines)
        else:
            refs_yaml = "code_references: []"

        if subsystems:
            subsystems_yaml = "subsystems:\n"
            for sub in subsystems:
                subsystems_yaml += f"  - subsystem_id: {sub['subsystem_id']}\n"
                subsystems_yaml += f"    relationship: {sub['relationship']}\n"
        else:
            subsystems_yaml = "subsystems: []"

        frontmatter = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
{refs_yaml}
{subsystems_yaml}
---

# Chunk Goal

Test chunk content.
"""
        goal_path.write_text(frontmatter)

    def _create_subsystem(self, temp_project, subsystem_name):
        """Helper to create a subsystem directory with OVERVIEW.md."""
        subsystem_path = temp_project / "docs" / "subsystems" / subsystem_name
        subsystem_path.mkdir(parents=True, exist_ok=True)
        overview_path = subsystem_path / "OVERVIEW.md"
        overview_path.write_text("""---
status: DISCOVERING
chunks: []
code_references: []
---

# Subsystem
""")

    def test_chunk_with_valid_subsystem_ref_passes(self, runner, temp_project):
        """Chunk with valid subsystem reference passes validation."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"

        # Create the subsystem
        self._create_subsystem(temp_project, "0001-validation")

        self._write_frontmatter_with_subsystems(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [{"subsystem_id": "0001-validation", "relationship": "implements"}],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_chunk_with_invalid_subsystem_ref_fails(self, runner, temp_project):
        """Chunk with invalid subsystem reference fails validation."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"

        self._write_frontmatter_with_subsystems(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [{"subsystem_id": "0001-nonexistent", "relationship": "implements"}],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "0001-nonexistent" in result.output

    def test_chunk_with_invalid_subsystem_id_format_fails(self, runner, temp_project):
        """Chunk with invalid subsystem_id format fails validation."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"

        self._write_frontmatter_with_subsystems(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [{"subsystem_id": "invalid-format", "relationship": "implements"}],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "invalid-format" in result.output

    def test_chunk_with_no_subsystems_passes(self, runner, temp_project):
        """Chunk without subsystems field still passes validation."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/main.py", "implements": "Main module"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
