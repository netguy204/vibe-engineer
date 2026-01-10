"""Tests for the 'chunk overlap' CLI command."""

import pathlib

import pytest

from ve import cli


def write_goal_frontmatter(
    chunk_path: pathlib.Path,
    status: str,
    code_references: list[dict],
    created_after: str | None = None,
):
    """Helper to write GOAL.md with frontmatter using symbolic reference format.

    Args:
        chunk_path: Path to chunk directory
        status: Chunk status (ACTIVE, IMPLEMENTING, etc.)
        code_references: List of dicts with 'ref' and 'implements' keys, e.g.:
            [{"ref": "src/main.py#Foo", "implements": "feature"}]
        created_after: Optional chunk ID that this chunk was created after (for causal ordering)
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

    # created_after must be a list in YAML format
    if created_after:
        created_after_yaml = f'created_after: ["{created_after}"]'
    else:
        created_after_yaml = "created_after: []"

    frontmatter = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
{refs_yaml}
narrative: null
subsystems: []
{created_after_yaml}
---

# Chunk Goal

Test chunk content.
"""
    goal_path.write_text(frontmatter)


# Chunk: docs/chunks/0044-remove_sequence_prefix - Updated for short_name only format
class TestOverlapCommand:
    """Tests for 've chunk overlap' CLI command."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["chunk", "overlap", "--help"])
        assert result.exit_code == 0
        assert "chunk_id" in result.output.lower() or "CHUNK_ID" in result.output
        assert "--project-dir" in result.output

    def test_nonexistent_chunk_exits_with_error(self, runner, temp_project):
        """Non-existent chunk ID exits non-zero with error message."""
        result = runner.invoke(
            cli,
            ["chunk", "overlap", "9999", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_chunk_with_no_code_references_outputs_nothing(self, runner, temp_project):
        """Chunk with no code_references outputs nothing, exits 0."""
        # Create a chunk
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        # The default template has empty code_references
        result = runner.invoke(
            cli,
            ["chunk", "overlap", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_no_active_chunks_with_lower_ids_outputs_nothing(self, runner, temp_project):
        """First chunk (no lower chunks) outputs nothing, exits 0."""
        # Create a chunk with code references
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        chunk_path = temp_project / "docs" / "chunks" / "feature"
        write_goal_frontmatter(chunk_path, "ACTIVE", [
            {"ref": "src/main.py#Foo", "implements": "test feature"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_overlapping_references_outputs_affected_chunks(self, runner, temp_project):
        """Chunk with overlapping references outputs affected chunk names."""
        # Create older chunk referencing src/main.py#Foo
        runner.invoke(
            cli,
            ["chunk", "start", "older", "--project-dir", str(temp_project)]
        )
        chunk1_path = temp_project / "docs" / "chunks" / "older"
        write_goal_frontmatter(chunk1_path, "ACTIVE", [
            {"ref": "src/main.py#Foo", "implements": "original implementation"}
        ])

        # Create newer chunk referencing src/main.py#Foo::bar (child of Foo)
        # This overlaps because Foo is parent of Foo::bar
        runner.invoke(
            cli,
            ["chunk", "start", "newer", "--project-dir", str(temp_project)]
        )
        chunk2_path = temp_project / "docs" / "chunks" / "newer"
        # Set created_after to establish causal ordering (newer is after older)
        write_goal_frontmatter(chunk2_path, "ACTIVE", [
            {"ref": "src/main.py#Foo::bar", "implements": "modified method"}
        ], created_after="older")

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "newer", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/chunks/older" in result.output

    def test_non_overlapping_references_outputs_nothing(self, runner, temp_project):
        """Chunk with non-overlapping references outputs nothing."""
        # Create chunk 0001 referencing src/main.py#Foo
        runner.invoke(
            cli,
            ["chunk", "start", "older", "--project-dir", str(temp_project)]
        )
        chunk1_path = temp_project / "docs" / "chunks" / "older"
        write_goal_frontmatter(chunk1_path, "ACTIVE", [
            {"ref": "src/main.py#Foo", "implements": "foo class"}
        ])

        # Create chunk 0002 referencing src/main.py#Bar (different symbol)
        # This does NOT overlap because Foo and Bar are siblings
        runner.invoke(
            cli,
            ["chunk", "start", "newer", "--project-dir", str(temp_project)]
        )
        chunk2_path = temp_project / "docs" / "chunks" / "newer"
        write_goal_frontmatter(chunk2_path, "ACTIVE", [
            {"ref": "src/main.py#Bar", "implements": "bar class"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "newer", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_chunk_id_accepts_full_directory_name(self, runner, temp_project):
        """Chunk ID accepts full directory name."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "overlap", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_project_dir_option_works(self, runner, temp_project):
        """--project-dir option works correctly."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "overlap", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_inactive_chunks_excluded_from_detection(self, runner, temp_project):
        """Chunks with status other than ACTIVE are excluded."""
        # Create chunk with SUPERSEDED status
        runner.invoke(
            cli,
            ["chunk", "start", "superseded", "--project-dir", str(temp_project)]
        )
        chunk1_path = temp_project / "docs" / "chunks" / "superseded"
        write_goal_frontmatter(chunk1_path, "SUPERSEDED", [
            {"ref": "src/main.py#Foo", "implements": "superseded code"}
        ])

        # Create chunk with ACTIVE status and overlapping refs
        runner.invoke(
            cli,
            ["chunk", "start", "active", "--project-dir", str(temp_project)]
        )
        chunk2_path = temp_project / "docs" / "chunks" / "active"
        write_goal_frontmatter(chunk2_path, "ACTIVE", [
            {"ref": "src/main.py#Foo", "implements": "active code"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Should NOT include superseded chunk
        assert "docs/chunks/superseded" not in result.output

    def test_different_files_no_overlap(self, runner, temp_project):
        """References to different files don't overlap."""
        # Create chunk 0001 referencing file A
        runner.invoke(
            cli,
            ["chunk", "start", "older", "--project-dir", str(temp_project)]
        )
        chunk1_path = temp_project / "docs" / "chunks" / "older"
        write_goal_frontmatter(chunk1_path, "ACTIVE", [
            {"ref": "src/main.py#Foo", "implements": "main code"}
        ])

        # Create chunk 0002 referencing file B
        runner.invoke(
            cli,
            ["chunk", "start", "newer", "--project-dir", str(temp_project)]
        )
        chunk2_path = temp_project / "docs" / "chunks" / "newer"
        write_goal_frontmatter(chunk2_path, "ACTIVE", [
            {"ref": "src/other.py#Bar", "implements": "other code"}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "newer", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_multiple_refs_in_same_file(self, runner, temp_project):
        """Multiple references in the same file are handled correctly."""
        # Create older chunk with multiple refs
        runner.invoke(
            cli,
            ["chunk", "start", "older", "--project-dir", str(temp_project)]
        )
        chunk1_path = temp_project / "docs" / "chunks" / "older"
        write_goal_frontmatter(chunk1_path, "ACTIVE", [
            {"ref": "src/main.py#Foo", "implements": "foo class"},
            {"ref": "src/main.py#Bar", "implements": "bar class"},
        ])

        # Create newer chunk with ref to child of Foo
        runner.invoke(
            cli,
            ["chunk", "start", "newer", "--project-dir", str(temp_project)]
        )
        chunk2_path = temp_project / "docs" / "chunks" / "newer"
        # Set created_after to establish causal ordering (newer is after older)
        write_goal_frontmatter(chunk2_path, "ACTIVE", [
            {"ref": "src/main.py#Foo::baz", "implements": "baz method"}
        ], created_after="older")

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "newer", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/chunks/older" in result.output
