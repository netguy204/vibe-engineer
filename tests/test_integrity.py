"""Tests for referential integrity validation.

# Chunk: docs/chunks/integrity_validate - Tests for integrity validation module
"""

import pathlib

import pytest

from conftest import make_ve_initialized_git_repo
from integrity import IntegrityValidator, validate_integrity


def write_chunk_goal(
    chunk_path: pathlib.Path,
    narrative: str | None = None,
    investigation: str | None = None,
    subsystems: list[dict] | None = None,
    friction_entries: list[dict] | None = None,
    depends_on: list[str] | None = None,
):
    """Helper to write a chunk GOAL.md with optional outbound references."""
    goal_path = chunk_path / "GOAL.md"

    frontmatter_lines = [
        "---",
        "status: IMPLEMENTING",
        "ticket: null",
        "parent_chunk: null",
        "code_paths: []",
        "code_references: []",
    ]

    if narrative:
        frontmatter_lines.append(f"narrative: {narrative}")
    else:
        frontmatter_lines.append("narrative: null")

    if investigation:
        frontmatter_lines.append(f"investigation: {investigation}")
    else:
        frontmatter_lines.append("investigation: null")

    if subsystems:
        frontmatter_lines.append("subsystems:")
        for sub in subsystems:
            frontmatter_lines.append(f"  - subsystem_id: {sub['subsystem_id']}")
            frontmatter_lines.append(f"    relationship: {sub.get('relationship', 'uses')}")
    else:
        frontmatter_lines.append("subsystems: []")

    if friction_entries:
        frontmatter_lines.append("friction_entries:")
        for entry in friction_entries:
            frontmatter_lines.append(f"  - entry_id: {entry['entry_id']}")
            frontmatter_lines.append(f"    scope: {entry.get('scope', 'full')}")
    else:
        frontmatter_lines.append("friction_entries: []")

    if depends_on:
        frontmatter_lines.append("depends_on:")
        for dep in depends_on:
            frontmatter_lines.append(f"  - {dep}")
    else:
        frontmatter_lines.append("depends_on: []")

    frontmatter_lines.append("created_after: []")
    frontmatter_lines.append("---")
    frontmatter_lines.append("")
    frontmatter_lines.append("# Test Chunk")

    goal_path.write_text("\n".join(frontmatter_lines))


def write_narrative_overview(
    narrative_path: pathlib.Path,
    proposed_chunks: list[dict] | None = None,
):
    """Helper to write a narrative OVERVIEW.md with proposed_chunks."""
    overview_path = narrative_path / "OVERVIEW.md"

    frontmatter_lines = [
        "---",
        "status: ACTIVE",
    ]

    if proposed_chunks:
        frontmatter_lines.append("proposed_chunks:")
        for i, chunk in enumerate(proposed_chunks):
            frontmatter_lines.append(f"  - prompt: \"Prompt {i}\"")
            if chunk.get("chunk_directory"):
                frontmatter_lines.append(f"    chunk_directory: {chunk['chunk_directory']}")
    else:
        frontmatter_lines.append("proposed_chunks: []")

    frontmatter_lines.append("created_after: []")
    frontmatter_lines.append("---")
    frontmatter_lines.append("")
    frontmatter_lines.append("# Test Narrative")

    overview_path.write_text("\n".join(frontmatter_lines))


def write_investigation_overview(
    investigation_path: pathlib.Path,
    proposed_chunks: list[dict] | None = None,
):
    """Helper to write an investigation OVERVIEW.md with proposed_chunks."""
    overview_path = investigation_path / "OVERVIEW.md"

    frontmatter_lines = [
        "---",
        "status: SOLVED",
        "trigger: \"Test trigger\"",
    ]

    if proposed_chunks:
        frontmatter_lines.append("proposed_chunks:")
        for i, chunk in enumerate(proposed_chunks):
            frontmatter_lines.append(f"  - prompt: \"Prompt {i}\"")
            if chunk.get("chunk_directory"):
                frontmatter_lines.append(f"    chunk_directory: {chunk['chunk_directory']}")
    else:
        frontmatter_lines.append("proposed_chunks: []")

    frontmatter_lines.append("created_after: []")
    frontmatter_lines.append("---")
    frontmatter_lines.append("")
    frontmatter_lines.append("# Test Investigation")

    overview_path.write_text("\n".join(frontmatter_lines))


def write_subsystem_overview(
    subsystem_path: pathlib.Path,
    chunks: list[dict] | None = None,
):
    """Helper to write a subsystem OVERVIEW.md with chunk references."""
    overview_path = subsystem_path / "OVERVIEW.md"

    frontmatter_lines = [
        "---",
        "status: DOCUMENTED",
    ]

    if chunks:
        frontmatter_lines.append("chunks:")
        for chunk in chunks:
            frontmatter_lines.append(f"  - chunk_id: {chunk['chunk_id']}")
            frontmatter_lines.append(f"    relationship: {chunk.get('relationship', 'implements')}")
    else:
        frontmatter_lines.append("chunks: []")

    frontmatter_lines.append("code_refs: []")
    frontmatter_lines.append("created_after: []")
    frontmatter_lines.append("---")
    frontmatter_lines.append("")
    frontmatter_lines.append("# Test Subsystem")

    overview_path.write_text("\n".join(frontmatter_lines))


def write_friction_log(
    project_path: pathlib.Path,
    entries: list[str] | None = None,
    proposed_chunks: list[dict] | None = None,
):
    """Helper to write a FRICTION.md with entries and proposed_chunks."""
    friction_path = project_path / "docs" / "trunk" / "FRICTION.md"
    friction_path.parent.mkdir(parents=True, exist_ok=True)

    frontmatter_lines = [
        "---",
        "themes: []",
    ]

    if proposed_chunks:
        frontmatter_lines.append("proposed_chunks:")
        for i, chunk in enumerate(proposed_chunks):
            frontmatter_lines.append(f"  - prompt: \"Prompt {i}\"")
            if chunk.get("chunk_directory"):
                frontmatter_lines.append(f"    chunk_directory: {chunk['chunk_directory']}")
            if chunk.get("addresses"):
                frontmatter_lines.append("    addresses:")
                for addr in chunk["addresses"]:
                    frontmatter_lines.append(f"      - {addr}")
    else:
        frontmatter_lines.append("proposed_chunks: []")

    frontmatter_lines.append("---")
    frontmatter_lines.append("")
    frontmatter_lines.append("# Friction Log")

    # Add entries
    if entries:
        for entry_id in entries:
            frontmatter_lines.append("")
            frontmatter_lines.append(f"### {entry_id}: 2026-01-31 [test-theme] Test Entry")
            frontmatter_lines.append("")
            frontmatter_lines.append("Test friction entry content.")

    friction_path.write_text("\n".join(frontmatter_lines))


class TestIntegrityValidatorBasic:
    """Basic tests for IntegrityValidator."""

    def test_empty_project_passes(self, temp_project):
        """Empty project with no artifacts passes validation."""
        make_ve_initialized_git_repo(temp_project)
        result = validate_integrity(temp_project)
        assert result.success
        assert len(result.errors) == 0

    def test_valid_chunk_passes(self, temp_project):
        """Chunk with no outbound refs passes."""
        make_ve_initialized_git_repo(temp_project)
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path)

        result = validate_integrity(temp_project)
        assert result.success
        assert result.chunks_scanned == 1

    def test_valid_chunk_with_narrative_ref(self, temp_project):
        """Chunk referencing existing narrative passes."""
        make_ve_initialized_git_repo(temp_project)

        # Create narrative
        narrative_path = temp_project / "docs" / "narratives" / "test_narrative"
        narrative_path.mkdir(parents=True)
        write_narrative_overview(narrative_path)

        # Create chunk referencing narrative
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, narrative="test_narrative")

        result = validate_integrity(temp_project)
        assert result.success

    def test_valid_chunk_with_investigation_ref(self, temp_project):
        """Chunk referencing existing investigation passes."""
        make_ve_initialized_git_repo(temp_project)

        # Create investigation
        investigation_path = temp_project / "docs" / "investigations" / "test_investigation"
        investigation_path.mkdir(parents=True)
        write_investigation_overview(investigation_path)

        # Create chunk referencing investigation
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, investigation="test_investigation")

        result = validate_integrity(temp_project)
        assert result.success


class TestIntegrityValidatorChunkOutbound:
    """Tests for chunk outbound reference validation."""

    def test_invalid_narrative_ref_fails(self, temp_project):
        """Chunk referencing non-existent narrative fails."""
        make_ve_initialized_git_repo(temp_project)

        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, narrative="nonexistent_narrative")

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "nonexistent_narrative" in result.errors[0].message
        assert result.errors[0].link_type == "chunk→narrative"

    def test_invalid_investigation_ref_fails(self, temp_project):
        """Chunk referencing non-existent investigation fails."""
        make_ve_initialized_git_repo(temp_project)

        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, investigation="nonexistent_investigation")

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "nonexistent_investigation" in result.errors[0].message
        assert result.errors[0].link_type == "chunk→investigation"

    def test_invalid_subsystem_ref_fails(self, temp_project):
        """Chunk referencing non-existent subsystem fails."""
        make_ve_initialized_git_repo(temp_project)

        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(
            chunk_path,
            subsystems=[{"subsystem_id": "nonexistent_subsystem", "relationship": "uses"}],
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "nonexistent_subsystem" in result.errors[0].message
        assert result.errors[0].link_type == "chunk→subsystem"

    def test_invalid_friction_entry_ref_fails(self, temp_project):
        """Chunk referencing non-existent friction entry fails."""
        make_ve_initialized_git_repo(temp_project)

        # Create empty friction log
        write_friction_log(temp_project, entries=["F001"])

        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(
            chunk_path,
            friction_entries=[{"entry_id": "F999", "scope": "full"}],
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "F999" in result.errors[0].message
        assert result.errors[0].link_type == "chunk→friction"

    def test_valid_friction_entry_ref_passes(self, temp_project):
        """Chunk referencing existing friction entry passes."""
        make_ve_initialized_git_repo(temp_project)

        # Create friction log with entry
        write_friction_log(temp_project, entries=["F001"])

        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(
            chunk_path,
            friction_entries=[{"entry_id": "F001", "scope": "full"}],
        )

        result = validate_integrity(temp_project)
        assert result.success

    def test_invalid_depends_on_ref_fails(self, temp_project):
        """Chunk with invalid depends_on reference fails."""
        make_ve_initialized_git_repo(temp_project)

        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, depends_on=["nonexistent_chunk"])

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "nonexistent_chunk" in result.errors[0].message
        assert result.errors[0].link_type == "chunk→chunk"


class TestIntegrityValidatorProposedChunks:
    """Tests for proposed_chunks validation in parent artifacts."""

    def test_narrative_valid_chunk_directory_passes(self, temp_project):
        """Narrative with valid chunk_directory passes."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path)

        # Create narrative referencing chunk
        narrative_path = temp_project / "docs" / "narratives" / "test_narrative"
        narrative_path.mkdir(parents=True)
        write_narrative_overview(
            narrative_path,
            proposed_chunks=[{"chunk_directory": "test_chunk"}],
        )

        result = validate_integrity(temp_project)
        assert result.success

    def test_narrative_invalid_chunk_directory_fails(self, temp_project):
        """Narrative with invalid chunk_directory fails."""
        make_ve_initialized_git_repo(temp_project)

        # Create narrative referencing non-existent chunk
        narrative_path = temp_project / "docs" / "narratives" / "test_narrative"
        narrative_path.mkdir(parents=True)
        write_narrative_overview(
            narrative_path,
            proposed_chunks=[{"chunk_directory": "nonexistent_chunk"}],
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "nonexistent_chunk" in result.errors[0].message
        assert result.errors[0].link_type == "narrative→chunk"

    def test_narrative_null_chunk_directory_passes(self, temp_project):
        """Narrative with null chunk_directory passes (chunk not yet created)."""
        make_ve_initialized_git_repo(temp_project)

        narrative_path = temp_project / "docs" / "narratives" / "test_narrative"
        narrative_path.mkdir(parents=True)
        write_narrative_overview(
            narrative_path,
            proposed_chunks=[{}],  # No chunk_directory
        )

        result = validate_integrity(temp_project)
        assert result.success

    def test_investigation_invalid_chunk_directory_fails(self, temp_project):
        """Investigation with invalid chunk_directory fails."""
        make_ve_initialized_git_repo(temp_project)

        investigation_path = temp_project / "docs" / "investigations" / "test_investigation"
        investigation_path.mkdir(parents=True)
        write_investigation_overview(
            investigation_path,
            proposed_chunks=[{"chunk_directory": "nonexistent_chunk"}],
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert result.errors[0].link_type == "investigation→chunk"

    def test_malformed_chunk_directory_detected(self, temp_project):
        """Malformed chunk_directory with prefix is detected."""
        make_ve_initialized_git_repo(temp_project)

        # Create the actual chunk
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path)

        investigation_path = temp_project / "docs" / "investigations" / "test_investigation"
        investigation_path.mkdir(parents=True)
        write_investigation_overview(
            investigation_path,
            # Malformed: includes docs/chunks/ prefix
            proposed_chunks=[{"chunk_directory": "docs/chunks/test_chunk"}],
        )

        result = validate_integrity(temp_project)
        assert not result.success
        # Should detect the malformed prefix
        assert any("Malformed" in e.message for e in result.errors)

    def test_friction_valid_chunk_directory_passes(self, temp_project):
        """Friction log with valid chunk_directory references passes validation."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path)

        # Create friction log referencing chunk
        write_friction_log(
            temp_project,
            proposed_chunks=[{"chunk_directory": "test_chunk"}],
        )

        result = validate_integrity(temp_project)
        assert result.success

    def test_friction_invalid_chunk_directory_fails(self, temp_project):
        """Friction log with stale chunk_directory reference fails with appropriate error."""
        make_ve_initialized_git_repo(temp_project)

        # Create friction log referencing non-existent chunk
        write_friction_log(
            temp_project,
            proposed_chunks=[{"chunk_directory": "nonexistent_chunk"}],
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "nonexistent_chunk" in result.errors[0].message
        assert result.errors[0].link_type == "friction→chunk"
        assert result.errors[0].source == "docs/trunk/FRICTION.md"
        assert result.errors[0].target == "docs/chunks/nonexistent_chunk"

    def test_friction_null_chunk_directory_passes(self, temp_project):
        """Friction log with null chunk_directory (chunk not yet created) passes validation."""
        make_ve_initialized_git_repo(temp_project)

        # Create friction log with proposed chunk that has no chunk_directory
        write_friction_log(
            temp_project,
            proposed_chunks=[{}],  # No chunk_directory (chunk not yet created)
        )

        result = validate_integrity(temp_project)
        assert result.success

    def test_friction_malformed_chunk_directory_detected(self, temp_project):
        """Friction log with docs/chunks/ prefix is detected as malformed."""
        make_ve_initialized_git_repo(temp_project)

        # Create the actual chunk
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path)

        # Create friction log with malformed chunk_directory
        write_friction_log(
            temp_project,
            # Malformed: includes docs/chunks/ prefix
            proposed_chunks=[{"chunk_directory": "docs/chunks/test_chunk"}],
        )

        result = validate_integrity(temp_project)
        assert not result.success
        # Should detect the malformed prefix
        assert any("Malformed" in e.message for e in result.errors)
        assert any(e.link_type == "friction→chunk" for e in result.errors)


class TestIntegrityValidatorSubsystemChunkRefs:
    """Tests for subsystem -> chunk reference validation."""

    def test_valid_subsystem_chunk_ref_passes(self, temp_project):
        """Subsystem referencing existing chunk passes."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path)

        # Create subsystem referencing chunk
        subsystem_path = temp_project / "docs" / "subsystems" / "test_subsystem"
        subsystem_path.mkdir(parents=True)
        write_subsystem_overview(
            subsystem_path,
            chunks=[{"chunk_id": "test_chunk", "relationship": "implements"}],
        )

        result = validate_integrity(temp_project)
        assert result.success

    def test_invalid_subsystem_chunk_ref_fails(self, temp_project):
        """Subsystem referencing non-existent chunk fails."""
        make_ve_initialized_git_repo(temp_project)

        subsystem_path = temp_project / "docs" / "subsystems" / "test_subsystem"
        subsystem_path.mkdir(parents=True)
        write_subsystem_overview(
            subsystem_path,
            chunks=[{"chunk_id": "nonexistent_chunk", "relationship": "implements"}],
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "nonexistent_chunk" in result.errors[0].message
        assert result.errors[0].link_type == "subsystem→chunk"


class TestIntegrityValidatorCodeBackrefs:
    """Tests for code backreference validation."""

    def test_valid_code_backref_passes(self, temp_project):
        """Code backreference to existing chunk passes."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path)

        # Create source file with backreference
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n# Chunk: docs/chunks/test_chunk - Test chunk\n'
        )

        result = validate_integrity(temp_project)
        assert result.success
        assert result.files_scanned == 1
        assert result.chunk_backrefs_found == 1

    def test_invalid_chunk_backref_fails(self, temp_project):
        """Code backreference to non-existent chunk fails."""
        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n# Chunk: docs/chunks/nonexistent_chunk - Test chunk\n'
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "nonexistent_chunk" in result.errors[0].message
        assert result.errors[0].link_type == "code→chunk"

    def test_valid_subsystem_backref_passes(self, temp_project):
        """Code backreference to existing subsystem passes."""
        make_ve_initialized_git_repo(temp_project)

        # Create subsystem
        subsystem_path = temp_project / "docs" / "subsystems" / "test_subsystem"
        subsystem_path.mkdir(parents=True)
        write_subsystem_overview(subsystem_path)

        # Create source file with backreference
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n# Subsystem: docs/subsystems/test_subsystem - Test\n'
        )

        result = validate_integrity(temp_project)
        assert result.success
        assert result.subsystem_backrefs_found == 1

    def test_invalid_subsystem_backref_fails(self, temp_project):
        """Code backreference to non-existent subsystem fails."""
        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n# Subsystem: docs/subsystems/nonexistent - Test\n'
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "nonexistent" in result.errors[0].message
        assert result.errors[0].link_type == "code→subsystem"

    def test_multiple_backrefs_in_file(self, temp_project):
        """Multiple backreferences in one file are all validated."""
        make_ve_initialized_git_repo(temp_project)

        # Create one chunk, not the other
        chunk_path = temp_project / "docs" / "chunks" / "valid_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path)

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n'
            "# Chunk: docs/chunks/valid_chunk - Valid\n"
            "# Chunk: docs/chunks/invalid_chunk - Invalid\n"
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert result.chunk_backrefs_found == 2

    def test_no_src_dir_passes(self, temp_project):
        """Project without src directory passes."""
        make_ve_initialized_git_repo(temp_project)

        result = validate_integrity(temp_project)
        assert result.success
        assert result.files_scanned == 0


class TestIntegrityValidatorMultipleErrors:
    """Tests for multiple error detection."""

    def test_multiple_errors_all_reported(self, temp_project):
        """Multiple integrity errors are all reported."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk with multiple invalid refs
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(
            chunk_path,
            narrative="invalid_narrative",
            investigation="invalid_investigation",
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 2


class TestIntegrityValidatorCLI:
    """Tests for the ve validate CLI command."""

    def test_validate_command_help(self, runner):
        """ve validate --help shows usage."""
        from ve import cli

        result = runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate referential integrity" in result.output

    def test_validate_empty_project(self, runner, temp_project):
        """ve validate passes on empty project."""
        from ve import cli

        make_ve_initialized_git_repo(temp_project)

        result = runner.invoke(cli, ["validate", "--project-dir", str(temp_project)])
        assert result.exit_code == 0
        assert "Validation passed" in result.output

    def test_validate_with_errors_fails(self, runner, temp_project):
        """ve validate fails with exit code 1 on errors."""
        from ve import cli

        make_ve_initialized_git_repo(temp_project)

        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, narrative="nonexistent")

        result = runner.invoke(cli, ["validate", "--project-dir", str(temp_project)])
        assert result.exit_code == 1
        assert "Validation failed" in result.output

    def test_validate_verbose_shows_stats(self, runner, temp_project):
        """ve validate --verbose shows statistics."""
        from ve import cli

        make_ve_initialized_git_repo(temp_project)

        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path)

        result = runner.invoke(
            cli, ["validate", "--verbose", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "Chunks: 1" in result.output
        assert "Scanning artifacts" in result.output
