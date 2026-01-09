"""Tests for Subsystems.find_overlapping_subsystems() business logic."""

import pytest


class TestFindOverlappingSubsystems:
    """Tests for Subsystems.find_overlapping_subsystems() method."""

    def _create_chunk_with_refs(self, temp_project, chunk_name, code_refs=None, code_paths=None):
        """Helper to create a chunk with code_references and/or code_paths."""
        chunk_path = temp_project / "docs" / "chunks" / chunk_name
        chunk_path.mkdir(parents=True, exist_ok=True)

        # Build frontmatter
        parts = ["status: IMPLEMENTING"]

        if code_refs:
            parts.append("code_references:")
            for ref in code_refs:
                parts.append(f'  - ref: "{ref["ref"]}"')
                parts.append(f'    implements: "{ref.get("implements", "Implementation")}"')
        else:
            parts.append("code_references: []")

        if code_paths:
            parts.append("code_paths:")
            for path in code_paths:
                parts.append(f"  - {path}")
        else:
            parts.append("code_paths: []")

        frontmatter = "\n".join(parts)
        (chunk_path / "GOAL.md").write_text(f"""---
{frontmatter}
---

# Chunk Goal
""")

    def _create_subsystem_with_refs(self, temp_project, subsystem_name, code_refs, status="DOCUMENTED"):
        """Helper to create a subsystem with code_references."""
        subsystem_path = temp_project / "docs" / "subsystems" / subsystem_name
        subsystem_path.mkdir(parents=True, exist_ok=True)

        if code_refs:
            refs_yaml = "code_references:"
            for ref in code_refs:
                refs_yaml += f'\n  - ref: "{ref["ref"]}"'
                refs_yaml += f'\n    implements: "{ref.get("implements", "Implementation")}"'
        else:
            refs_yaml = "code_references: []"

        (subsystem_path / "OVERVIEW.md").write_text(f"""---
status: {status}
chunks: []
{refs_yaml}
---

# Subsystem
""")

    def test_no_overlap_when_chunk_has_no_code_references(self, temp_project):
        """Returns empty list when chunk has no code_references."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Create chunk with empty code_references
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=None)

        # Create subsystem with code_references
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert result == []

    def test_no_overlap_when_no_subsystems_exist(self, temp_project):
        """Returns empty list when no subsystems exist."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Create chunk with code_references
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert result == []

    def test_file_level_overlap_detection(self, temp_project):
        """Detects overlap when chunk references file and subsystem references symbol in that file."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Chunk references the file only (no symbol)
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py", "implements": "Foo module"}
        ])

        # Subsystem references a symbol within that file
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert len(result) == 1
        assert result[0]["subsystem_id"] == "0001-validation"

    def test_symbol_level_overlap_parent_child(self, temp_project):
        """Detects overlap when chunk reference is child of subsystem reference."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Chunk references a method (child)
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar::method", "implements": "Method implementation"}
        ])

        # Subsystem references the class (parent)
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert len(result) == 1
        assert result[0]["subsystem_id"] == "0001-validation"

    def test_symbol_level_overlap_child_parent(self, temp_project):
        """Detects overlap when chunk reference is parent of subsystem reference."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Chunk references the class (parent)
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        # Subsystem references a method (child)
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/foo.py#Bar::method", "implements": "Method implementation"}
        ])

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert len(result) == 1
        assert result[0]["subsystem_id"] == "0001-validation"

    def test_no_overlap_for_unrelated_files(self, temp_project):
        """No overlap when chunk and subsystem reference different files."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Chunk references one file
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py", "implements": "Foo module"}
        ])

        # Subsystem references a different file
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/bar.py", "implements": "Bar module"}
        ])

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert result == []

    def test_returns_subsystem_status_in_results(self, temp_project):
        """Output includes subsystem ID and status."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Create overlapping chunk and subsystem
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        self._create_subsystem_with_refs(
            temp_project, "0001-validation",
            [{"ref": "src/foo.py#Bar", "implements": "Bar class"}],
            status="STABLE"
        )

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert len(result) == 1
        assert result[0]["subsystem_id"] == "0001-validation"
        assert result[0]["status"] == "STABLE"
        assert "overlapping_refs" in result[0]

    def test_handles_chunk_using_code_paths_only(self, temp_project):
        """Falls back to code_paths when code_references is empty."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Chunk has only code_paths, no code_references
        self._create_chunk_with_refs(
            temp_project, "0001-feature",
            code_refs=None,
            code_paths=["src/foo.py"]
        )

        # Subsystem references a symbol in that file
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert len(result) == 1
        assert result[0]["subsystem_id"] == "0001-validation"

    def test_handles_multiple_overlapping_subsystems(self, temp_project):
        """Returns all matching subsystems when multiple overlap."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Chunk references two files
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar", "implements": "Bar class"},
            {"ref": "src/baz.py#Qux", "implements": "Qux class"},
        ])

        # First subsystem overlaps with src/foo.py
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ], status="STABLE")

        # Second subsystem overlaps with src/baz.py
        self._create_subsystem_with_refs(temp_project, "0002-processing", [
            {"ref": "src/baz.py#Qux", "implements": "Qux class"}
        ], status="DOCUMENTED")

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert len(result) == 2

        # Extract subsystem IDs for easier assertion
        subsystem_ids = {r["subsystem_id"] for r in result}
        assert subsystem_ids == {"0001-validation", "0002-processing"}

    def test_raises_error_for_nonexistent_chunk(self, temp_project):
        """Raises ValueError when chunk doesn't exist."""
        from subsystems import Subsystems
        from chunks import Chunks

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        with pytest.raises(ValueError) as exc_info:
            subsystems.find_overlapping_subsystems("9999-nonexistent", chunks)
        assert "not found" in str(exc_info.value).lower()

    def test_exact_symbol_match(self, temp_project):
        """Detects overlap when chunk and subsystem reference exact same symbol."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Both reference exact same symbol
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar::baz", "implements": "Baz method"}
        ])

        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/foo.py#Bar::baz", "implements": "Baz method"}
        ])

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert len(result) == 1
        assert result[0]["subsystem_id"] == "0001-validation"

    def test_overlapping_refs_includes_specific_matches(self, temp_project):
        """overlapping_refs field includes the specific references that match."""
        from subsystems import Subsystems
        from chunks import Chunks

        # Chunk references a method
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar::method", "implements": "Method impl"}
        ])

        # Subsystem references the class (parent)
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        subsystems = Subsystems(temp_project)
        chunks = Chunks(temp_project)

        result = subsystems.find_overlapping_subsystems("0001-feature", chunks)
        assert len(result) == 1
        assert "overlapping_refs" in result[0]
        # The overlapping_refs should include the subsystem's reference that matched
        assert "src/foo.py#Bar" in result[0]["overlapping_refs"]
