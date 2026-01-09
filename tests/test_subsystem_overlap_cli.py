"""Tests for the 've subsystem overlap' CLI command."""

from ve import cli


class TestSubsystemOverlapNoOverlap:
    """Tests for 've subsystem overlap' when no overlap exists."""

    def _create_chunk_with_refs(self, temp_project, chunk_name, code_refs=None, code_paths=None):
        """Helper to create a chunk with code_references and/or code_paths."""
        chunk_path = temp_project / "docs" / "chunks" / chunk_name
        chunk_path.mkdir(parents=True, exist_ok=True)

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

    def test_exits_0_with_no_output_when_no_overlap(self, runner, temp_project):
        """Exits 0 with no output when no overlap detected."""
        # Create chunk referencing one file
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py", "implements": "Foo module"}
        ])

        # Create subsystem referencing different file
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/bar.py", "implements": "Bar module"}
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "0001-feature", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert result.output.strip() == ""


class TestSubsystemOverlapWithOverlap:
    """Tests for 've subsystem overlap' when overlap exists."""

    def _create_chunk_with_refs(self, temp_project, chunk_name, code_refs=None, code_paths=None):
        """Helper to create a chunk with code_references and/or code_paths."""
        chunk_path = temp_project / "docs" / "chunks" / chunk_name
        chunk_path.mkdir(parents=True, exist_ok=True)

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

    def test_exits_0_listing_overlapping_subsystems(self, runner, temp_project):
        """Exits 0 and lists overlapping subsystems when overlap detected."""
        # Create overlapping chunk and subsystem
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        self._create_subsystem_with_refs(
            temp_project, "0001-validation",
            [{"ref": "src/foo.py#Bar", "implements": "Bar class"}],
            status="STABLE"
        )

        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "0001-feature", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "docs/subsystems/0001-validation" in result.output

    def test_shows_subsystem_status(self, runner, temp_project):
        """Each output line includes subsystem status."""
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        self._create_subsystem_with_refs(
            temp_project, "0001-validation",
            [{"ref": "src/foo.py#Bar", "implements": "Bar class"}],
            status="STABLE"
        )

        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "0001-feature", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "[STABLE]" in result.output

    def test_lists_multiple_overlapping_subsystems(self, runner, temp_project):
        """Lists all overlapping subsystems when multiple exist."""
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

        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "0001-feature", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "docs/subsystems/0001-validation" in result.output
        assert "[STABLE]" in result.output
        assert "docs/subsystems/0002-processing" in result.output
        assert "[DOCUMENTED]" in result.output


class TestSubsystemOverlapErrors:
    """Tests for error handling."""

    def test_exits_1_for_invalid_chunk_id(self, runner, temp_project):
        """Exits 1 with error message when chunk not found."""
        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "9999-nonexistent", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()
