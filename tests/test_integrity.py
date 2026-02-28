"""Tests for referential integrity validation.

# Chunk: docs/chunks/integrity_validate - Tests for integrity validation module
# Chunk: docs/chunks/validate_external_chunks - Tests for external chunk validation behavior
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
    code_references: list[dict] | None = None,
):
    """Helper to write a chunk GOAL.md with optional outbound references."""
    goal_path = chunk_path / "GOAL.md"

    frontmatter_lines = [
        "---",
        "status: IMPLEMENTING",
        "ticket: null",
        "parent_chunk: null",
        "code_paths: []",
    ]

    if code_references:
        frontmatter_lines.append("code_references:")
        for ref in code_references:
            frontmatter_lines.append(f"  - ref: {ref['ref']}")
            frontmatter_lines.append(f"    implements: \"{ref.get('implements', 'Implementation')}\"")
    else:
        frontmatter_lines.append("code_references: []")

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


# Chunk: docs/chunks/integrity_code_backrefs - Tests for line number tracking in backreference errors
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

    def test_error_includes_line_number_in_source(self, temp_project):
        """Code backreference error includes line number in source field."""
        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        # Backreference on line 3
        (src_dir / "test.py").write_text(
            '"""Test module."""\n'
            "\n"
            "# Chunk: docs/chunks/nonexistent_chunk - Test chunk\n"
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        # Source should include line number
        assert result.errors[0].source == "src/test.py:3"

    def test_error_message_includes_line_number(self, temp_project):
        """Code backreference error message mentions the line number."""
        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n'
            "\n"
            "# Chunk: docs/chunks/nonexistent_chunk - Test chunk\n"
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        # Message should mention line number
        assert "line 3" in result.errors[0].message

    def test_multiple_errors_report_distinct_line_numbers(self, temp_project):
        """Multiple broken backreferences report correct distinct line numbers."""
        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        # Two broken backreferences at different line numbers
        (src_dir / "test.py").write_text(
            '"""Test module."""\n'  # line 1
            "\n"  # line 2
            "# Chunk: docs/chunks/nonexistent_a - First\n"  # line 3
            "def foo():\n"  # line 4
            "    pass\n"  # line 5
            "\n"  # line 6
            "# Chunk: docs/chunks/nonexistent_b - Second\n"  # line 7
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 2

        # Check that errors have distinct line numbers
        sources = {e.source for e in result.errors}
        assert "src/test.py:3" in sources
        assert "src/test.py:7" in sources

        # Check messages include line numbers
        messages = [e.message for e in result.errors]
        assert any("line 3" in m for m in messages)
        assert any("line 7" in m for m in messages)

    def test_subsystem_backref_error_includes_line_number(self, temp_project):
        """Subsystem backreference error includes line number."""
        make_ve_initialized_git_repo(temp_project)

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n'  # line 1
            "\n"  # line 2
            "\n"  # line 3
            "# Subsystem: docs/subsystems/nonexistent - Test\n"  # line 4
        )

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert result.errors[0].source == "src/test.py:4"
        assert "line 4" in result.errors[0].message


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


# Chunk: docs/chunks/integrity_bidirectional - Tests for bidirectional consistency warnings
class TestIntegrityValidatorBidirectional:
    """Tests for bidirectional consistency warnings."""

    def test_chunk_narrative_bidirectional_warning(self, temp_project):
        """Chunk references narrative but narrative's proposed_chunks doesn't list chunk → expect warning."""
        make_ve_initialized_git_repo(temp_project)

        # Create narrative WITHOUT this chunk in proposed_chunks
        narrative_path = temp_project / "docs" / "narratives" / "test_narrative"
        narrative_path.mkdir(parents=True)
        write_narrative_overview(narrative_path, proposed_chunks=[])  # Empty - no chunk listed

        # Create chunk referencing the narrative
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, narrative="test_narrative")

        result = validate_integrity(temp_project)
        # Should pass (no errors) but have warnings
        assert result.success  # Bidirectional issues are warnings, not errors
        assert len(result.warnings) == 1
        assert result.warnings[0].link_type == "chunk↔narrative"
        assert "test_narrative" in result.warnings[0].message
        assert "proposed_chunks" in result.warnings[0].message

    def test_chunk_narrative_bidirectional_valid(self, temp_project):
        """Both directions exist → no warning."""
        make_ve_initialized_git_repo(temp_project)

        # Create narrative WITH this chunk in proposed_chunks
        narrative_path = temp_project / "docs" / "narratives" / "test_narrative"
        narrative_path.mkdir(parents=True)
        write_narrative_overview(
            narrative_path,
            proposed_chunks=[{"chunk_directory": "test_chunk"}],
        )

        # Create chunk referencing the narrative
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, narrative="test_narrative")

        result = validate_integrity(temp_project)
        assert result.success
        assert len(result.warnings) == 0

    def test_chunk_investigation_bidirectional_warning(self, temp_project):
        """Chunk references investigation but investigation doesn't list chunk → expect warning."""
        make_ve_initialized_git_repo(temp_project)

        # Create investigation WITHOUT this chunk in proposed_chunks
        investigation_path = temp_project / "docs" / "investigations" / "test_investigation"
        investigation_path.mkdir(parents=True)
        write_investigation_overview(investigation_path, proposed_chunks=[])  # Empty

        # Create chunk referencing the investigation
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, investigation="test_investigation")

        result = validate_integrity(temp_project)
        assert result.success  # Bidirectional issues are warnings, not errors
        assert len(result.warnings) == 1
        assert result.warnings[0].link_type == "chunk↔investigation"
        assert "test_investigation" in result.warnings[0].message
        assert "proposed_chunks" in result.warnings[0].message

    def test_chunk_investigation_bidirectional_valid(self, temp_project):
        """Both directions exist → no warning."""
        make_ve_initialized_git_repo(temp_project)

        # Create investigation WITH this chunk in proposed_chunks
        investigation_path = temp_project / "docs" / "investigations" / "test_investigation"
        investigation_path.mkdir(parents=True)
        write_investigation_overview(
            investigation_path,
            proposed_chunks=[{"chunk_directory": "test_chunk"}],
        )

        # Create chunk referencing the investigation
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, investigation="test_investigation")

        result = validate_integrity(temp_project)
        assert result.success
        assert len(result.warnings) == 0

    def test_code_chunk_bidirectional_warning(self, temp_project):
        """Code has # Chunk: backref but chunk's code_references doesn't reference that file → expect warning."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk WITHOUT code_references to src/test.py
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, code_references=[])  # Empty - no code refs

        # Create source file with backreference to the chunk
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n# Chunk: docs/chunks/test_chunk - Test chunk\n'
        )

        result = validate_integrity(temp_project)
        assert result.success  # Bidirectional issues are warnings, not errors
        assert len(result.warnings) == 1
        assert result.warnings[0].link_type == "code↔chunk"
        assert "test_chunk" in result.warnings[0].message
        assert "code_references" in result.warnings[0].message

    def test_code_chunk_bidirectional_valid(self, temp_project):
        """Code backref and chunk code_reference both exist → no warning."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk WITH code_references to src/test.py
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(
            chunk_path,
            code_references=[{"ref": "src/test.py#TestClass", "implements": "Test logic"}],
        )

        # Create source file with backreference to the chunk
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n# Chunk: docs/chunks/test_chunk - Test chunk\n'
        )

        result = validate_integrity(temp_project)
        assert result.success
        assert len(result.warnings) == 0

    def test_code_chunk_bidirectional_matches_file_path_only(self, temp_project):
        """File path match is sufficient even if symbols differ."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk with code_references to src/test.py#ClassName::method
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(
            chunk_path,
            code_references=[{"ref": "src/test.py#ClassName::method", "implements": "Method impl"}],
        )

        # Create source file with backreference (module level, not method level)
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n# Chunk: docs/chunks/test_chunk - Module level ref\n'
        )

        result = validate_integrity(temp_project)
        assert result.success
        # No warning - file path match is sufficient
        assert len(result.warnings) == 0

    def test_strict_mode_promotes_bidirectional_warnings(self, runner, temp_project):
        """CLI --strict flag promotes warnings to errors."""
        from ve import cli

        make_ve_initialized_git_repo(temp_project)

        # Create narrative WITHOUT this chunk in proposed_chunks
        narrative_path = temp_project / "docs" / "narratives" / "test_narrative"
        narrative_path.mkdir(parents=True)
        write_narrative_overview(narrative_path, proposed_chunks=[])

        # Create chunk referencing the narrative
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, narrative="test_narrative")

        # Without --strict: should pass (exit 0) with warnings
        result = runner.invoke(cli, ["validate", "--project-dir", str(temp_project)])
        assert result.exit_code == 0
        assert "warning" in result.output.lower() or "Warning" in result.output

        # With --strict: should fail (exit 1) because warnings become errors
        result = runner.invoke(
            cli, ["validate", "--strict", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Validation failed" in result.output


def write_external_chunk(chunk_path: pathlib.Path, repo: str = "acme/ext-repo", artifact_id: str | None = None):
    """Helper to write an external chunk (external.yaml instead of GOAL.md).

    External chunks are pointers to canonical artifacts in other repositories.
    They contain only external.yaml, not GOAL.md.

    Args:
        chunk_path: Path to the chunk directory.
        repo: External repository reference in org/repo format.
        artifact_id: Artifact ID in the external repo. Defaults to chunk_path.name.
    """
    import yaml

    chunk_path.mkdir(parents=True, exist_ok=True)
    external_yaml_path = chunk_path / "external.yaml"

    if artifact_id is None:
        artifact_id = chunk_path.name

    data = {
        "artifact_type": "chunk",
        "artifact_id": artifact_id,
        "repo": repo,
        "track": "main",
    }

    with open(external_yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


class TestIntegrityValidatorExternalChunks:
    """Tests for external chunk validation behavior."""

    def test_project_with_only_external_chunks_passes(self, temp_project):
        """A project with only external chunks (no local chunks) passes validation."""
        make_ve_initialized_git_repo(temp_project)

        # Create external chunk (external.yaml, no GOAL.md)
        external_chunk_path = temp_project / "docs" / "chunks" / "xr_external_feature"
        write_external_chunk(external_chunk_path)

        result = validate_integrity(temp_project)
        assert result.success
        assert len(result.errors) == 0
        # External chunks should be skipped, not counted in chunks_scanned
        assert result.chunks_scanned == 0
        assert result.external_chunks_skipped == 1

    def test_mixed_local_and_external_chunks(self, temp_project):
        """Mixed local and external chunks: only local chunks are validated."""
        make_ve_initialized_git_repo(temp_project)

        # Create local chunk
        local_chunk_path = temp_project / "docs" / "chunks" / "local_feature"
        local_chunk_path.mkdir(parents=True)
        write_chunk_goal(local_chunk_path)

        # Create external chunk
        external_chunk_path = temp_project / "docs" / "chunks" / "xr_external_feature"
        write_external_chunk(external_chunk_path)

        result = validate_integrity(temp_project)
        assert result.success
        assert result.chunks_scanned == 1  # Only local chunk
        assert result.external_chunks_skipped == 1

    def test_external_chunks_skipped_count_reported(self, temp_project):
        """Multiple external chunks are all counted in skipped count."""
        make_ve_initialized_git_repo(temp_project)

        # Create multiple external chunks
        for name in ["xr_feature_a", "xr_feature_b", "xr_feature_c"]:
            external_chunk_path = temp_project / "docs" / "chunks" / name
            write_external_chunk(external_chunk_path)

        result = validate_integrity(temp_project)
        assert result.success
        assert result.chunks_scanned == 0
        assert result.external_chunks_skipped == 3

    def test_local_chunk_with_error_still_fails_with_external_present(self, temp_project):
        """Local chunk errors are still reported even when external chunks exist."""
        make_ve_initialized_git_repo(temp_project)

        # Create local chunk with invalid reference
        local_chunk_path = temp_project / "docs" / "chunks" / "local_broken"
        local_chunk_path.mkdir(parents=True)
        write_chunk_goal(local_chunk_path, narrative="nonexistent_narrative")

        # Create external chunk
        external_chunk_path = temp_project / "docs" / "chunks" / "xr_external"
        write_external_chunk(external_chunk_path)

        result = validate_integrity(temp_project)
        assert not result.success
        assert len(result.errors) == 1
        assert "nonexistent_narrative" in result.errors[0].message
        assert result.chunks_scanned == 1  # Only local chunk
        assert result.external_chunks_skipped == 1

    def test_cli_verbose_shows_external_chunks_skipped(self, runner, temp_project):
        """CLI --verbose output shows external chunks skipped count."""
        from ve import cli

        make_ve_initialized_git_repo(temp_project)

        # Create external chunk
        external_chunk_path = temp_project / "docs" / "chunks" / "xr_external"
        write_external_chunk(external_chunk_path)

        result = runner.invoke(
            cli, ["validate", "--verbose", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "External chunks skipped: 1" in result.output

    def test_code_backref_to_external_chunk_passes(self, temp_project):
        """Code backreference to an external chunk directory should pass.

        External chunks exist as directories with external.yaml, so code can
        still reference them. The validation should recognize that the chunk
        directory exists (even if it's external).
        """
        make_ve_initialized_git_repo(temp_project)

        # Create external chunk
        external_chunk_path = temp_project / "docs" / "chunks" / "xr_feature"
        write_external_chunk(external_chunk_path)

        # Create source file with backreference to the external chunk
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text(
            '"""Test module."""\n# Chunk: docs/chunks/xr_feature - External feature\n'
        )

        result = validate_integrity(temp_project)
        # External chunk directories should be recognized in the chunk index
        # so code backreferences to them should not produce errors
        assert result.success
        assert len(result.errors) == 0
        assert result.chunk_backrefs_found == 1


# Chunk: docs/chunks/integrity_subsystem_bidir - Tests for chunk↔subsystem bidirectional warnings
class TestIntegrityValidatorChunkSubsystemBidirectional:
    """Tests for chunk↔subsystem bidirectional consistency warnings."""

    def test_chunk_subsystem_bidirectional_warning(self, temp_project):
        """Chunk references subsystem but subsystem's chunks doesn't list the chunk → expect warning."""
        make_ve_initialized_git_repo(temp_project)

        # Create subsystem WITHOUT this chunk in its chunks field
        subsystem_path = temp_project / "docs" / "subsystems" / "test_subsystem"
        subsystem_path.mkdir(parents=True)
        write_subsystem_overview(subsystem_path, chunks=[])  # Empty - chunk not listed

        # Create chunk referencing the subsystem
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(
            chunk_path,
            subsystems=[{"subsystem_id": "test_subsystem", "relationship": "implements"}],
        )

        result = validate_integrity(temp_project)
        # Should pass (no errors) but have warnings
        assert result.success  # Bidirectional issues are warnings, not errors
        assert len(result.warnings) == 1
        assert result.warnings[0].link_type == "chunk↔subsystem"
        assert "test_subsystem" in result.warnings[0].message
        assert "chunks" in result.warnings[0].message

    def test_chunk_subsystem_bidirectional_valid(self, temp_project):
        """Both directions exist → no warning."""
        make_ve_initialized_git_repo(temp_project)

        # Create subsystem WITH this chunk in its chunks field
        subsystem_path = temp_project / "docs" / "subsystems" / "test_subsystem"
        subsystem_path.mkdir(parents=True)
        write_subsystem_overview(
            subsystem_path,
            chunks=[{"chunk_id": "test_chunk", "relationship": "implements"}],
        )

        # Create chunk referencing the subsystem
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(
            chunk_path,
            subsystems=[{"subsystem_id": "test_subsystem", "relationship": "implements"}],
        )

        result = validate_integrity(temp_project)
        assert result.success
        assert len(result.warnings) == 0

    def test_subsystem_chunk_bidirectional_warning(self, temp_project):
        """Subsystem lists chunk in its chunks field but chunk's subsystems doesn't reference subsystem → expect warning."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk WITHOUT subsystem reference
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, subsystems=[])  # Empty - no subsystem reference

        # Create subsystem listing the chunk
        subsystem_path = temp_project / "docs" / "subsystems" / "test_subsystem"
        subsystem_path.mkdir(parents=True)
        write_subsystem_overview(
            subsystem_path,
            chunks=[{"chunk_id": "test_chunk", "relationship": "implements"}],
        )

        result = validate_integrity(temp_project)
        # Should pass (no errors) but have warnings
        assert result.success  # Bidirectional issues are warnings, not errors
        assert len(result.warnings) == 1
        assert result.warnings[0].link_type == "subsystem↔chunk"
        assert "test_chunk" in result.warnings[0].message
        assert "subsystems" in result.warnings[0].message

    def test_subsystem_chunk_bidirectional_valid(self, temp_project):
        """Both directions exist → no warning."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk WITH subsystem reference
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(
            chunk_path,
            subsystems=[{"subsystem_id": "test_subsystem", "relationship": "implements"}],
        )

        # Create subsystem listing the chunk
        subsystem_path = temp_project / "docs" / "subsystems" / "test_subsystem"
        subsystem_path.mkdir(parents=True)
        write_subsystem_overview(
            subsystem_path,
            chunks=[{"chunk_id": "test_chunk", "relationship": "implements"}],
        )

        result = validate_integrity(temp_project)
        assert result.success
        assert len(result.warnings) == 0

    def test_subsystem_chunk_bidirectional_warning_external_chunk_skipped(self, temp_project):
        """Subsystem lists external chunk → no bidirectional warning (external chunks don't have GOAL.md)."""
        make_ve_initialized_git_repo(temp_project)

        # Create external chunk (no GOAL.md, just external.yaml)
        external_chunk_path = temp_project / "docs" / "chunks" / "xr_external"
        write_external_chunk(external_chunk_path)

        # Create subsystem listing the external chunk
        subsystem_path = temp_project / "docs" / "subsystems" / "test_subsystem"
        subsystem_path.mkdir(parents=True)
        write_subsystem_overview(
            subsystem_path,
            chunks=[{"chunk_id": "xr_external", "relationship": "implements"}],
        )

        result = validate_integrity(temp_project)
        # Should pass with no warnings - external chunks don't have subsystems field
        assert result.success
        assert len(result.warnings) == 0
        assert len(result.errors) == 0

    def test_multiple_subsystems_each_checked(self, temp_project):
        """Chunk referencing multiple subsystems: each is checked for bidirectionality."""
        make_ve_initialized_git_repo(temp_project)

        # Create subsystem A WITH this chunk in its chunks field
        subsystem_a_path = temp_project / "docs" / "subsystems" / "subsystem_a"
        subsystem_a_path.mkdir(parents=True)
        write_subsystem_overview(
            subsystem_a_path,
            chunks=[{"chunk_id": "test_chunk", "relationship": "implements"}],
        )

        # Create subsystem B WITHOUT this chunk in its chunks field
        subsystem_b_path = temp_project / "docs" / "subsystems" / "subsystem_b"
        subsystem_b_path.mkdir(parents=True)
        write_subsystem_overview(subsystem_b_path, chunks=[])  # Missing chunk

        # Create chunk referencing both subsystems
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(
            chunk_path,
            subsystems=[
                {"subsystem_id": "subsystem_a", "relationship": "implements"},
                {"subsystem_id": "subsystem_b", "relationship": "uses"},
            ],
        )

        result = validate_integrity(temp_project)
        assert result.success  # Bidirectional issues are warnings, not errors
        # Should have one warning for subsystem_b
        assert len(result.warnings) == 1
        assert result.warnings[0].link_type == "chunk↔subsystem"
        assert "subsystem_b" in result.warnings[0].message


# Chunk: docs/chunks/integrity_deprecate_standalone - Tests for IntegrityValidator.validate_chunk()
class TestIntegrityValidatorSingleChunk:
    """Tests for IntegrityValidator.validate_chunk() method."""

    def test_validate_chunk_returns_errors_for_invalid_refs(self, temp_project):
        """validate_chunk returns errors for invalid references."""
        make_ve_initialized_git_repo(temp_project)

        # Create chunk with invalid narrative reference
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, narrative="nonexistent_narrative")

        validator = IntegrityValidator(temp_project)
        errors, warnings = validator.validate_chunk("test_chunk")

        assert len(errors) == 1
        assert errors[0].link_type == "chunk→narrative"
        assert "nonexistent_narrative" in errors[0].message

    def test_validate_chunk_returns_warnings_for_bidirectional_issues(self, temp_project):
        """validate_chunk returns warnings for bidirectional consistency issues."""
        make_ve_initialized_git_repo(temp_project)

        # Create narrative WITHOUT this chunk in proposed_chunks
        narrative_path = temp_project / "docs" / "narratives" / "test_narrative"
        narrative_path.mkdir(parents=True)
        write_narrative_overview(narrative_path, proposed_chunks=[])

        # Create chunk referencing the narrative
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path, narrative="test_narrative")

        validator = IntegrityValidator(temp_project)
        errors, warnings = validator.validate_chunk("test_chunk")

        # No errors (narrative exists)
        assert len(errors) == 0
        # But warning for bidirectional issue
        assert len(warnings) == 1
        assert warnings[0].link_type == "chunk↔narrative"

    def test_validate_chunk_returns_empty_for_valid_chunk(self, temp_project):
        """validate_chunk returns empty lists for valid chunk."""
        make_ve_initialized_git_repo(temp_project)

        # Create valid chunk with no outbound references
        chunk_path = temp_project / "docs" / "chunks" / "test_chunk"
        chunk_path.mkdir(parents=True)
        write_chunk_goal(chunk_path)

        validator = IntegrityValidator(temp_project)
        errors, warnings = validator.validate_chunk("test_chunk")

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_chunk_handles_nonexistent_chunk(self, temp_project):
        """validate_chunk handles nonexistent chunk gracefully."""
        make_ve_initialized_git_repo(temp_project)

        validator = IntegrityValidator(temp_project)
        errors, warnings = validator.validate_chunk("nonexistent")

        # Should return an error about parsing failure
        assert len(errors) == 1
        assert "frontmatter" in errors[0].message.lower() or "parse" in errors[0].message.lower()
