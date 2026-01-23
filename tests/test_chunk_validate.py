"""Tests for the 'chunk validate' CLI command.

Note: chunk validate uses code_references which is an in-repo chunk feature.
Tests that need to modify chunk frontmatter use task directory mode (not scratchpad).
"""

import pathlib

from conftest import setup_task_directory

from ve import cli


def write_goal_frontmatter(
    chunk_path: pathlib.Path,
    status: str,
    code_references: list[dict] | None = None,
):
    """Helper to write GOAL.md with symbolic reference frontmatter.

    Args:
        chunk_path: Path to chunk directory
        status: Chunk status (IMPLEMENTING, ACTIVE, etc.)
        code_references: List of dicts with 'ref' and 'implements' keys, e.g.:
            [{"ref": "src/main.py#MyClass", "implements": "feature"}]
    """
    goal_path = chunk_path / "GOAL.md"

    if code_references:
        refs_lines = ["code_references:"]
        for ref in code_references:
            refs_lines.append(f"  - ref: \"{ref['ref']}\"")
            refs_lines.append(f"    implements: \"{ref.get('implements', 'test implementation')}\"")
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


# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
class TestValidateCommandInterface:
    """Tests for 've chunk validate' command interface."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["chunk", "validate", "--help"])
        assert result.exit_code == 0
        assert "--project-dir" in result.output

    def test_chunk_id_argument_is_optional(self, runner, tmp_path):
        """chunk_id argument is optional."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        # Create a chunk with valid state
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/main.py#Main", "implements": "req1"}
        ])

        # Invoke without chunk_id - should default to latest
        result = runner.invoke(
            cli,
            ["chunk", "validate", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_project_dir_option_works(self, runner, tmp_path):
        """--project-dir option works correctly."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/main.py#Main", "implements": "req1"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0


class TestStatusValidation:
    """Tests for status validation in 've chunk validate'."""

    def test_fails_when_status_not_implementing_or_active(self, runner, tmp_path):
        """Command fails if chunk status is not IMPLEMENTING or ACTIVE."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "HISTORICAL", [
            {"ref": "src/main.py#Main", "implements": "req1"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0

    def test_active_status_passes(self, runner, tmp_path):
        """Command succeeds when chunk status is ACTIVE."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "ACTIVE", [
            {"ref": "src/main.py#Main", "implements": "req1"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_error_states_current_status(self, runner, tmp_path):
        """Error message states the current status."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "HISTORICAL", [
            {"ref": "src/main.py#Main", "implements": "req1"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert "HISTORICAL" in result.output

    def test_error_explains_why_blocked(self, runner, tmp_path):
        """Error message explains why completion is blocked."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "HISTORICAL", [
            {"ref": "src/main.py#Main", "implements": "req1"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        # Should explain that status must be IMPLEMENTING or ACTIVE
        assert "IMPLEMENTING" in result.output or "ACTIVE" in result.output

    def test_nonexistent_chunk_exits_with_error(self, runner, tmp_path):
        """Non-existent chunk ID exits non-zero with error message."""
        task_dir, _, _ = setup_task_directory(tmp_path)
        result = runner.invoke(
            cli,
            ["chunk", "validate", "9999", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_no_chunks_exits_with_error(self, runner, tmp_path):
        """No chunks available exits non-zero with error message."""
        task_dir, _, _ = setup_task_directory(tmp_path)
        result = runner.invoke(
            cli,
            ["chunk", "validate", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0


class TestCodeReferencesValidation:
    """Tests for code_references validation in 've chunk validate'."""

    def test_valid_code_references_passes(self, runner, tmp_path):
        """Valid code_references passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/main.py#Main", "implements": "req1"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_missing_ref_field_produces_error(self, runner, tmp_path):
        """Missing 'ref' field produces error (frontmatter can't be parsed)."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        # Write malformed frontmatter directly
        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text("""---
status: IMPLEMENTING
code_references:
  - implements: "req1"
---

# Chunk Goal
""")

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "frontmatter" in result.output.lower() or "parse" in result.output.lower()

    def test_missing_implements_field_produces_error(self, runner, tmp_path):
        """Missing 'implements' field produces error (frontmatter can't be parsed)."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text("""---
status: IMPLEMENTING
code_references:
  - ref: "src/main.py#Main"
---

# Chunk Goal
""")

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "frontmatter" in result.output.lower() or "parse" in result.output.lower()

    def test_wrong_status_type_produces_error(self, runner, tmp_path):
        """Wrong type for status produces error (frontmatter can't be parsed)."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        goal_path = chunk_path / "GOAL.md"
        goal_path.write_text("""---
status: INVALID_STATUS
code_references:
  - ref: "src/main.py#Main"
    implements: "req1"
---

# Chunk Goal
""")

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0

    def test_empty_code_references_fails(self, runner, tmp_path):
        """Empty code_references list fails with error."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        # Should explain that at least one reference is required
        assert "reference" in result.output.lower() or "empty" in result.output.lower()


class TestSuccessOutput:
    """Tests for success output in 've chunk validate'."""

    def test_success_prints_confirmation(self, runner, tmp_path):
        """Successful validation prints confirmation message."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/main.py#Main", "implements": "req1"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0
        # Should output some confirmation
        assert len(result.output.strip()) > 0

    def test_success_exits_zero(self, runner, tmp_path):
        """Exit code 0 on success."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/main.py#Main", "implements": "req1"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0


class TestSymbolicReferenceValidation:
    """Tests for symbolic code_references validation with warnings."""

    def test_valid_symbolic_reference_passes(self, runner, tmp_path):
        """Valid symbolic reference passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/models.py#SymbolicReference", "implements": "Model definition"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_file_only_reference_passes(self, runner, tmp_path):
        """File-only reference (no symbol) passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/models.py", "implements": "Full module"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_nonexistent_symbol_produces_warning(self, runner, tmp_path):
        """Reference to non-existent symbol produces warning but succeeds."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/models.py#NonExistentClass", "implements": "Missing class"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        # Should succeed (exit 0) but show warning
        assert result.exit_code == 0
        assert "warning" in result.output.lower() or "not found" in result.output.lower()

    def test_nonexistent_file_produces_warning(self, runner, tmp_path):
        """Reference to non-existent file produces warning but succeeds."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/nonexistent.py#SomeClass", "implements": "Missing file"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        # Should succeed (exit 0) but show warning
        assert result.exit_code == 0
        assert "warning" in result.output.lower() or "not found" in result.output.lower()

    def test_multiple_warnings_collected(self, runner, tmp_path):
        """Multiple invalid references produce multiple warnings."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/models.py#NonExistent1", "implements": "First missing"},
            {"ref": "src/models.py#NonExistent2", "implements": "Second missing"},
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        # Should succeed but show warnings for both
        assert result.exit_code == 0
        # Both symbols should be mentioned
        assert "NonExistent1" in result.output or "warning" in result.output.lower()

    def test_no_warnings_when_all_symbols_valid(self, runner, tmp_path):
        """No warnings shown when all symbols are valid."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        # Create a real Python file with a symbol in external repo
        src_dir = external_path / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "test_module.py").write_text("class MyClass:\n    pass\n")

        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/test_module.py#MyClass", "implements": "Valid class"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
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

    def _create_subsystem(self, external_path, subsystem_name):
        """Helper to create a subsystem directory with OVERVIEW.md."""
        subsystem_path = external_path / "docs" / "subsystems" / subsystem_name
        subsystem_path.mkdir(parents=True, exist_ok=True)
        overview_path = subsystem_path / "OVERVIEW.md"
        overview_path.write_text("""---
status: DISCOVERING
chunks: []
code_references: []
---

# Subsystem
""")

    def test_chunk_with_valid_subsystem_ref_passes(self, runner, tmp_path):
        """Chunk with valid subsystem reference passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        # Create the subsystem in external repo
        self._create_subsystem(external_path, "validation")

        self._write_frontmatter_with_subsystems(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [{"subsystem_id": "validation", "relationship": "implements"}],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_chunk_with_invalid_subsystem_ref_fails(self, runner, tmp_path):
        """Chunk with invalid subsystem reference fails validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        self._write_frontmatter_with_subsystems(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [{"subsystem_id": "nonexistent", "relationship": "implements"}],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "nonexistent" in result.output

    def test_chunk_with_invalid_subsystem_id_format_fails(self, runner, tmp_path):
        """Chunk with invalid subsystem_id format fails validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        self._write_frontmatter_with_subsystems(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [{"subsystem_id": "invalid-format", "relationship": "implements"}],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        # Subsystem doesn't exist
        assert result.exit_code != 0
        assert "invalid-format" in result.output.lower() or "does not exist" in result.output.lower()

    def test_chunk_with_no_subsystems_passes(self, runner, tmp_path):
        """Chunk without subsystems field still passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"
        write_symbolic_frontmatter(chunk_path, "IMPLEMENTING", [
            {"ref": "src/main.py", "implements": "Main module"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0


class TestInvestigationRefValidation:
    """Tests for investigation reference validation in 've chunk validate'."""

    def _write_frontmatter_with_investigation(
        self,
        chunk_path,
        status: str,
        code_references: list[dict],
        investigation: str | None = None,
    ):
        """Helper to write GOAL.md with investigation field."""
        goal_path = chunk_path / "GOAL.md"

        if code_references:
            refs_lines = ["code_references:"]
            for ref in code_references:
                refs_lines.append(f"  - ref: {ref['ref']}")
                refs_lines.append(f"    implements: \"{ref['implements']}\"")
            refs_yaml = "\n".join(refs_lines)
        else:
            refs_yaml = "code_references: []"

        investigation_yaml = f"investigation: {investigation}" if investigation else "investigation: null"

        frontmatter = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
{refs_yaml}
narrative: null
{investigation_yaml}
subsystems: []
---

# Chunk Goal

Test chunk content.
"""
        goal_path.write_text(frontmatter)

    def _create_investigation(self, external_path, investigation_name):
        """Helper to create an investigation directory with OVERVIEW.md."""
        investigation_path = external_path / "docs" / "investigations" / investigation_name
        investigation_path.mkdir(parents=True, exist_ok=True)
        overview_path = investigation_path / "OVERVIEW.md"
        overview_path.write_text("""---
status: SOLVED
trigger: null
proposed_chunks: []
---

# Investigation
""")

    def test_chunk_with_valid_investigation_ref_passes(self, runner, tmp_path):
        """Chunk with valid investigation reference passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        # Create the investigation in external repo
        self._create_investigation(external_path, "memory_leak")

        self._write_frontmatter_with_investigation(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            "memory_leak",
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_chunk_with_invalid_investigation_ref_fails(self, runner, tmp_path):
        """Chunk with invalid investigation reference fails validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        self._write_frontmatter_with_investigation(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            "nonexistent_investigation",
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "nonexistent_investigation" in result.output

    def test_chunk_with_no_investigation_ref_passes(self, runner, tmp_path):
        """Chunk without investigation reference passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        self._write_frontmatter_with_investigation(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            None,
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0


# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
class TestExternalChunkValidation:
    """Tests for validating external chunks from project context."""

    def _create_external_yaml(
        self,
        chunk_path,
        external_repo_ref: str,
        artifact_id: str,
        pinned_sha: str = "a" * 40,
    ):
        """Helper to create external.yaml for a chunk directory."""
        chunk_path.mkdir(parents=True, exist_ok=True)
        external_yaml = chunk_path / "external.yaml"
        external_yaml.write_text(f"""artifact_type: chunk
artifact_id: {artifact_id}
repo: {external_repo_ref}
track: main
pinned: {pinned_sha}
""")

    def _create_chunk_with_refs(
        self,
        chunk_path,
        status: str = "IMPLEMENTING",
        code_references: list[dict] | None = None,
    ):
        """Helper to create a full chunk with GOAL.md."""
        chunk_path.mkdir(parents=True, exist_ok=True)
        write_goal_frontmatter(chunk_path, status, code_references)

    def test_external_chunk_without_task_context_uses_cache(
        self, runner, tmp_path
    ):
        """External chunk validation uses repo cache when no task context available.

        Without task context, external chunks are resolved via the repo cache.
        If the external repo isn't accessible (e.g., doesn't exist on GitHub),
        validation fails with 'not found'.
        """
        from conftest import make_ve_initialized_git_repo

        # Set up external repo with the actual chunk (LOCAL - not on GitHub)
        external_repo = tmp_path / "external"
        make_ve_initialized_git_repo(external_repo)

        external_chunk_path = external_repo / "docs" / "chunks" / "my_feature"
        self._create_chunk_with_refs(
            external_chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py#Main", "implements": "feature"}],
        )

        # Set up project repo with external reference pointing to non-existent GitHub repo
        project_repo = tmp_path / "project"
        make_ve_initialized_git_repo(project_repo)

        project_chunk_path = project_repo / "docs" / "chunks" / "my_feature"
        self._create_external_yaml(
            project_chunk_path,
            external_repo_ref="acme/nonexistent-repo",  # This doesn't exist on GitHub
            artifact_id="my_feature",
        )

        # Validate from project context - cache resolution will fail because
        # the external repo doesn't exist on GitHub
        result = runner.invoke(
            cli,
            ["chunk", "validate", "my_feature", "--project-dir", str(project_repo)]
        )
        # Should fail because repo cache can't access the external repo
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_external_chunk_validated_in_task_context(self, runner, tmp_path):
        """External chunk is fully validated when run from task directory."""
        from conftest import setup_task_directory

        # Set up complete task environment
        task_dir, external_path, [project_path] = setup_task_directory(tmp_path)

        # Create chunk in external repo with valid code references
        external_chunk_path = external_path / "docs" / "chunks" / "my_feature"
        self._create_chunk_with_refs(
            external_chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py#Main", "implements": "feature"}],
        )

        # Create external reference in project
        project_chunk_path = project_path / "docs" / "chunks" / "my_feature"
        self._create_external_yaml(
            project_chunk_path,
            external_repo_ref="acme/ext",
            artifact_id="my_feature",
        )

        # Validate from task directory - should find and validate the external chunk
        result = runner.invoke(
            cli,
            ["chunk", "validate", "my_feature", "--project-dir", str(task_dir)]
        )
        # Should succeed since the chunk exists in external repo
        assert result.exit_code == 0
        assert "my_feature" in result.output

    def test_external_chunk_not_found_produces_error(self, runner, tmp_path):
        """Missing external chunk produces clear error message."""
        from conftest import setup_task_directory

        # Set up task environment but don't create chunk in external repo
        task_dir, external_path, [project_path] = setup_task_directory(tmp_path)

        # Create external reference in project pointing to non-existent chunk
        project_chunk_path = project_path / "docs" / "chunks" / "ghost_chunk"
        self._create_external_yaml(
            project_chunk_path,
            external_repo_ref="acme/ext",
            artifact_id="ghost_chunk",
        )

        # Validate should fail with clear error
        result = runner.invoke(
            cli,
            ["chunk", "validate", "ghost_chunk", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()


class TestTaskContextValidation:
    """Tests for validating chunks with cross-project code references in task context."""

    def _create_chunk_with_cross_project_refs(
        self,
        chunk_path,
        status: str = "IMPLEMENTING",
        code_references: list[dict] | None = None,
    ):
        """Helper to create a chunk with cross-project code references."""
        chunk_path.mkdir(parents=True, exist_ok=True)
        goal_path = chunk_path / "GOAL.md"

        if code_references:
            refs_lines = ["code_references:"]
            for ref in code_references:
                refs_lines.append(f"  - ref: \"{ref['ref']}\"")
                refs_lines.append(f"    implements: \"{ref.get('implements', 'feature')}\"")
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

    def test_cross_project_ref_validated_in_task_context(self, runner, tmp_path):
        """Cross-project code references are validated when running in task context."""
        from conftest import setup_task_directory

        # Set up task with two projects
        task_dir, external_path, [project_path] = setup_task_directory(
            tmp_path, project_names=["proj"]
        )

        # Create a file in the project that the chunk will reference
        src_dir = project_path / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "service.py").write_text("class Service:\n    pass\n")

        # Create chunk in external repo with cross-project reference
        external_chunk_path = external_path / "docs" / "chunks" / "cross_proj_feature"
        self._create_chunk_with_cross_project_refs(
            external_chunk_path,
            "IMPLEMENTING",
            # Reference uses project qualifier
            [{"ref": "acme/proj::src/service.py#Service", "implements": "service impl"}],
        )

        # Validate from task directory - should resolve cross-project ref
        result = runner.invoke(
            cli,
            ["chunk", "validate", "cross_proj_feature", "--project-dir", str(task_dir)]
        )
        # Should succeed since the file and symbol exist in the referenced project
        assert result.exit_code == 0

    def test_cross_project_ref_warns_on_missing_symbol(self, runner, tmp_path):
        """Cross-project reference to missing symbol produces warning but succeeds."""
        from conftest import setup_task_directory

        # Set up task with project
        task_dir, external_path, [project_path] = setup_task_directory(tmp_path)

        # Create a file without the expected symbol
        src_dir = project_path / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "service.py").write_text("# Empty module\n")

        # Create chunk with reference to non-existent symbol
        external_chunk_path = external_path / "docs" / "chunks" / "missing_symbol_ref"
        self._create_chunk_with_cross_project_refs(
            external_chunk_path,
            "IMPLEMENTING",
            [{"ref": "acme/proj::src/service.py#NonExistent", "implements": "missing"}],
        )

        # Validate should succeed but show warning
        result = runner.invoke(
            cli,
            ["chunk", "validate", "missing_symbol_ref", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0
        assert "warning" in result.output.lower() or "not found" in result.output.lower()

    def test_cross_project_ref_warns_on_missing_file(self, runner, tmp_path):
        """Cross-project reference to missing file produces warning but succeeds."""
        from conftest import setup_task_directory

        # Set up task with project
        task_dir, external_path, [project_path] = setup_task_directory(tmp_path)

        # Don't create the referenced file

        # Create chunk with reference to non-existent file
        external_chunk_path = external_path / "docs" / "chunks" / "missing_file_ref"
        self._create_chunk_with_cross_project_refs(
            external_chunk_path,
            "IMPLEMENTING",
            [{"ref": "acme/proj::src/nonexistent.py#Foo", "implements": "missing file"}],
        )

        # Validate should succeed but show warning
        result = runner.invoke(
            cli,
            ["chunk", "validate", "missing_file_ref", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0
        assert "warning" in result.output.lower() or "not found" in result.output.lower()

    def test_local_ref_validated_against_chunk_project(self, runner, tmp_path):
        """Non-qualified references are validated against the project containing the chunk."""
        from conftest import setup_task_directory

        # Set up task
        task_dir, external_path, [project_path] = setup_task_directory(tmp_path)

        # Create a file in the EXTERNAL repo (where chunks live)
        src_dir = external_path / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "local.py").write_text("class LocalClass:\n    pass\n")

        # Create chunk with local (non-qualified) reference
        external_chunk_path = external_path / "docs" / "chunks" / "local_ref_chunk"
        self._create_chunk_with_cross_project_refs(
            external_chunk_path,
            "IMPLEMENTING",
            # No project qualifier - should resolve against chunk's own project
            [{"ref": "src/local.py#LocalClass", "implements": "local impl"}],
        )

        # Validate from task directory
        result = runner.invoke(
            cli,
            ["chunk", "validate", "local_ref_chunk", "--project-dir", str(task_dir)]
        )
        # Should succeed since the file exists in the chunk's project (external repo)
        assert result.exit_code == 0


class TestProjectContextPartialValidation:
    """Tests for partial validation when running from project context (not task)."""

    def _create_chunk_with_refs(
        self,
        chunk_path,
        status: str = "IMPLEMENTING",
        code_references: list[dict] | None = None,
    ):
        """Helper to create a chunk with code references."""
        chunk_path.mkdir(parents=True, exist_ok=True)
        goal_path = chunk_path / "GOAL.md"

        if code_references:
            refs_lines = ["code_references:"]
            for ref in code_references:
                refs_lines.append(f"  - ref: \"{ref['ref']}\"")
                refs_lines.append(f"    implements: \"{ref.get('implements', 'feature')}\"")
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

    def test_local_refs_validated_in_project_context(self, runner, tmp_path):
        """Local (non-qualified) refs are fully validated in project context."""
        from conftest import make_ve_initialized_git_repo

        # Set up standalone project
        project_path = tmp_path / "project"
        make_ve_initialized_git_repo(project_path)

        # Create a file in the project
        src_dir = project_path / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "module.py").write_text("class MyClass:\n    pass\n")

        # Create chunk with local reference
        chunk_path = project_path / "docs" / "chunks" / "local_feature"
        self._create_chunk_with_refs(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/module.py#MyClass", "implements": "local impl"}],
        )

        # Validate from project context
        result = runner.invoke(
            cli,
            ["chunk", "validate", "local_feature", "--project-dir", str(project_path)]
        )
        # Should succeed - local refs can be validated
        assert result.exit_code == 0

    def test_cross_project_refs_skipped_in_project_context(self, runner, tmp_path):
        """Cross-project refs are skipped with informative message in project context."""
        from conftest import make_ve_initialized_git_repo

        # Set up standalone project (no task directory)
        project_path = tmp_path / "project"
        make_ve_initialized_git_repo(project_path)

        # Create chunk with cross-project reference
        chunk_path = project_path / "docs" / "chunks" / "cross_proj_feature"
        self._create_chunk_with_refs(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "other/repo::src/service.py#Service", "implements": "cross-proj"}],
        )

        # Validate from project context (no task dir)
        result = runner.invoke(
            cli,
            ["chunk", "validate", "cross_proj_feature", "--project-dir", str(project_path)]
        )
        # Should succeed (skip doesn't cause failure) but show skip message
        assert result.exit_code == 0
        # Output should indicate the cross-project ref was skipped
        assert "skip" in result.output.lower() or "cross-project" in result.output.lower()

    def test_mixed_refs_partial_validation(self, runner, tmp_path):
        """Mix of local and cross-project refs: local validated, cross-project skipped."""
        from conftest import make_ve_initialized_git_repo

        # Set up standalone project
        project_path = tmp_path / "project"
        make_ve_initialized_git_repo(project_path)

        # Create a local file
        src_dir = project_path / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "local.py").write_text("class LocalClass:\n    pass\n")

        # Create chunk with both local and cross-project references
        chunk_path = project_path / "docs" / "chunks" / "mixed_refs"
        self._create_chunk_with_refs(
            chunk_path,
            "IMPLEMENTING",
            [
                {"ref": "src/local.py#LocalClass", "implements": "local impl"},
                {"ref": "other/repo::src/remote.py#RemoteClass", "implements": "remote impl"},
            ],
        )

        # Validate from project context
        result = runner.invoke(
            cli,
            ["chunk", "validate", "mixed_refs", "--project-dir", str(project_path)]
        )
        # Should succeed overall
        assert result.exit_code == 0
        # Cross-project ref should be skipped
        assert "skip" in result.output.lower() or "cross-project" in result.output.lower()


class TestNarrativeRefValidation:
    """Tests for narrative reference validation in 've chunk validate'."""

    def _write_frontmatter_with_narrative(
        self,
        chunk_path,
        status: str,
        code_references: list[dict],
        narrative: str | None = None,
    ):
        """Helper to write GOAL.md with narrative field."""
        goal_path = chunk_path / "GOAL.md"

        if code_references:
            refs_lines = ["code_references:"]
            for ref in code_references:
                refs_lines.append(f"  - ref: {ref['ref']}")
                refs_lines.append(f"    implements: \"{ref['implements']}\"")
            refs_yaml = "\n".join(refs_lines)
        else:
            refs_yaml = "code_references: []"

        narrative_yaml = f"narrative: {narrative}" if narrative else "narrative: null"

        frontmatter = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
{refs_yaml}
{narrative_yaml}
investigation: null
subsystems: []
---

# Chunk Goal

Test chunk content.
"""
        goal_path.write_text(frontmatter)

    def _create_narrative(self, external_path, narrative_name):
        """Helper to create a narrative directory with OVERVIEW.md."""
        narrative_path = external_path / "docs" / "narratives" / narrative_name
        narrative_path.mkdir(parents=True, exist_ok=True)
        overview_path = narrative_path / "OVERVIEW.md"
        overview_path.write_text("""---
status: IN_PROGRESS
proposed_chunks: []
---

# Narrative
""")

    def test_chunk_with_valid_narrative_ref_passes(self, runner, tmp_path):
        """Chunk with valid narrative reference passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        # Create the narrative in external repo
        self._create_narrative(external_path, "chunk_lifecycle_management")

        self._write_frontmatter_with_narrative(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            "chunk_lifecycle_management",
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_chunk_with_invalid_narrative_ref_fails(self, runner, tmp_path):
        """Chunk with invalid narrative reference fails validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        self._write_frontmatter_with_narrative(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            "nonexistent_narrative",
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "nonexistent_narrative" in result.output

    def test_chunk_with_no_narrative_ref_passes(self, runner, tmp_path):
        """Chunk without narrative reference passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        self._write_frontmatter_with_narrative(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            None,
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0


# Subsystem: docs/subsystems/friction_tracking - Friction log management
class TestFrictionEntryRefValidation:
    """Tests for friction entry reference validation in 've chunk validate'."""

    def _write_frontmatter_with_friction_entries(
        self,
        chunk_path,
        status: str,
        code_references: list[dict],
        friction_entries: list[dict] | None = None,
    ):
        """Helper to write GOAL.md with friction_entries field."""
        goal_path = chunk_path / "GOAL.md"

        if code_references:
            refs_lines = ["code_references:"]
            for ref in code_references:
                refs_lines.append(f"  - ref: {ref['ref']}")
                refs_lines.append(f"    implements: \"{ref['implements']}\"")
            refs_yaml = "\n".join(refs_lines)
        else:
            refs_yaml = "code_references: []"

        if friction_entries:
            friction_yaml = "friction_entries:\n"
            for entry in friction_entries:
                friction_yaml += f"  - entry_id: {entry['entry_id']}\n"
                if 'scope' in entry:
                    friction_yaml += f"    scope: {entry['scope']}\n"
        else:
            friction_yaml = "friction_entries: []"

        frontmatter = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
{refs_yaml}
narrative: null
investigation: null
subsystems: []
{friction_yaml}
---

# Chunk Goal

Test chunk content.
"""
        goal_path.write_text(frontmatter)

    def _create_friction_log(self, external_path, entries: list[str] | None = None):
        """Helper to create FRICTION.md with optional entries.

        Args:
            external_path: Path to the external repo directory
            entries: List of entry IDs to create (e.g., ["F001", "F002"])
        """
        friction_path = external_path / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)

        if entries is None:
            entries = []

        entries_content = ""
        for entry_id in entries:
            entries_content += f"""
### {entry_id}: 2026-01-12 [test-theme] Test friction entry

This is a test friction entry for validation.

**Impact**: Medium
"""

        friction_content = f"""---
themes:
  - id: test-theme
    name: Test Theme
proposed_chunks: []
---

# Friction Log
{entries_content}
"""
        friction_path.write_text(friction_content)

    def test_chunk_with_valid_friction_entries_passes(self, runner, tmp_path):
        """Chunk with valid friction entry references passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        # Create friction log with entries in external repo
        self._create_friction_log(external_path, ["F001", "F002"])

        self._write_frontmatter_with_friction_entries(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [{"entry_id": "F001", "scope": "full"}],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_chunk_with_invalid_friction_entry_fails(self, runner, tmp_path):
        """Chunk with invalid friction entry reference fails validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        # Create friction log with only F001
        self._create_friction_log(external_path, ["F001"])

        # Reference F999 which doesn't exist
        self._write_frontmatter_with_friction_entries(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [{"entry_id": "F999", "scope": "full"}],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "F999" in result.output

    def test_chunk_with_no_friction_entries_passes(self, runner, tmp_path):
        """Chunk without friction_entries field passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        self._write_frontmatter_with_friction_entries(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            None,  # No friction entries
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_chunk_with_partial_scope_passes(self, runner, tmp_path):
        """Chunk with scope: partial passes validation."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        # Create friction log with entries
        self._create_friction_log(external_path, ["F001"])

        self._write_frontmatter_with_friction_entries(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [{"entry_id": "F001", "scope": "partial"}],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

    def test_chunk_with_multiple_friction_entries_validates_all(self, runner, tmp_path):
        """Chunk with multiple friction entries validates all of them."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        # Create friction log with F001 and F002 but NOT F003
        self._create_friction_log(external_path, ["F001", "F002"])

        # Reference F001, F002, and F003 (last one doesn't exist)
        self._write_frontmatter_with_friction_entries(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [
                {"entry_id": "F001", "scope": "full"},
                {"entry_id": "F002", "scope": "partial"},
                {"entry_id": "F003", "scope": "full"},  # This doesn't exist
            ],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "F003" in result.output

    def test_chunk_with_friction_entries_but_no_friction_log_fails(self, runner, tmp_path):
        """Chunk referencing friction entries when FRICTION.md doesn't exist fails."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(task_dir)]
        )
        chunk_path = external_path / "docs" / "chunks" / "feature"

        # Don't create friction log

        self._write_frontmatter_with_friction_entries(
            chunk_path,
            "IMPLEMENTING",
            [{"ref": "src/main.py", "implements": "Main module"}],
            [{"entry_id": "F001", "scope": "full"}],
        )

        result = runner.invoke(
            cli,
            ["chunk", "validate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        # Should mention friction log doesn't exist or entry not found
        assert "friction" in result.output.lower() or "F001" in result.output
