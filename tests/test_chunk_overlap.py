"""Tests for the 'chunk overlap' CLI command."""

import pathlib

from ve import cli


def write_goal_frontmatter(chunk_path: pathlib.Path, status: str, code_references: list[dict]):
    """Helper to write GOAL.md with frontmatter using the real format.

    Args:
        chunk_path: Path to chunk directory
        status: Chunk status (ACTIVE, COMPLETED, etc.)
        code_references: List of dicts with 'file' and 'ranges' keys, e.g.:
            [{"file": "src/main.py", "ranges": [{"lines": "10-20"}]}]
    """
    goal_path = chunk_path / "GOAL.md"

    if code_references:
        refs_lines = ["code_references:"]
        for ref in code_references:
            refs_lines.append(f"  - file: {ref['file']}")
            refs_lines.append("    ranges:")
            for r in ref.get("ranges", []):
                refs_lines.append(f"      - lines: {r['lines']}")
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
            ["chunk", "overlap", "0001", "--project-dir", str(temp_project)]
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
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        write_goal_frontmatter(chunk_path, "ACTIVE", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_overlapping_references_outputs_affected_chunks(self, runner, temp_project):
        """Chunk with overlapping references outputs affected chunk names."""
        # Create chunk 0001 (older) with references to lines 50-60
        runner.invoke(
            cli,
            ["chunk", "start", "older", "--project-dir", str(temp_project)]
        )
        chunk1_path = temp_project / "docs" / "chunks" / "0001-older"
        write_goal_frontmatter(chunk1_path, "ACTIVE", [
            {"file": "src/main.py", "ranges": [{"lines": "50-60"}]}
        ])

        # Create chunk 0002 (newer) with references to lines 10-20
        # This overlaps because 10 <= 60 (newer's earliest <= older's latest)
        runner.invoke(
            cli,
            ["chunk", "start", "newer", "--project-dir", str(temp_project)]
        )
        chunk2_path = temp_project / "docs" / "chunks" / "0002-newer"
        write_goal_frontmatter(chunk2_path, "ACTIVE", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "0002", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/chunks/0001-older" in result.output

    def test_non_overlapping_references_outputs_nothing(self, runner, temp_project):
        """Chunk with non-overlapping references outputs nothing."""
        # Create chunk 0001 with references to lines 10-20
        runner.invoke(
            cli,
            ["chunk", "start", "older", "--project-dir", str(temp_project)]
        )
        chunk1_path = temp_project / "docs" / "chunks" / "0001-older"
        write_goal_frontmatter(chunk1_path, "ACTIVE", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20"}]}
        ])

        # Create chunk 0002 with references to lines 100-110
        # This does NOT overlap because 100 > 20 (newer's earliest > older's latest)
        runner.invoke(
            cli,
            ["chunk", "start", "newer", "--project-dir", str(temp_project)]
        )
        chunk2_path = temp_project / "docs" / "chunks" / "0002-newer"
        write_goal_frontmatter(chunk2_path, "ACTIVE", [
            {"file": "src/main.py", "ranges": [{"lines": "100-110"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "0002", "--project-dir", str(temp_project)]
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
            ["chunk", "overlap", "0001-feature", "--project-dir", str(temp_project)]
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
            ["chunk", "overlap", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

    def test_inactive_chunks_excluded_from_detection(self, runner, temp_project):
        """Chunks with status other than ACTIVE are excluded."""
        # Create chunk 0001 with COMPLETED status
        runner.invoke(
            cli,
            ["chunk", "start", "completed", "--project-dir", str(temp_project)]
        )
        chunk1_path = temp_project / "docs" / "chunks" / "0001-completed"
        write_goal_frontmatter(chunk1_path, "COMPLETED", [
            {"file": "src/main.py", "ranges": [{"lines": "50-60"}]}
        ])

        # Create chunk 0002 with ACTIVE status and overlapping refs
        runner.invoke(
            cli,
            ["chunk", "start", "active", "--project-dir", str(temp_project)]
        )
        chunk2_path = temp_project / "docs" / "chunks" / "0002-active"
        write_goal_frontmatter(chunk2_path, "ACTIVE", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "0002", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Should NOT include completed chunk
        assert "docs/chunks/0001-completed" not in result.output

    def test_different_files_no_overlap(self, runner, temp_project):
        """References to different files don't overlap."""
        # Create chunk 0001 referencing file A
        runner.invoke(
            cli,
            ["chunk", "start", "older", "--project-dir", str(temp_project)]
        )
        chunk1_path = temp_project / "docs" / "chunks" / "0001-older"
        write_goal_frontmatter(chunk1_path, "ACTIVE", [
            {"file": "src/main.py", "ranges": [{"lines": "10-20"}]}
        ])

        # Create chunk 0002 referencing file B
        runner.invoke(
            cli,
            ["chunk", "start", "newer", "--project-dir", str(temp_project)]
        )
        chunk2_path = temp_project / "docs" / "chunks" / "0002-newer"
        write_goal_frontmatter(chunk2_path, "ACTIVE", [
            {"file": "src/other.py", "ranges": [{"lines": "10-20"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "0002", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_multiple_ranges_in_same_file(self, runner, temp_project):
        """Multiple ranges in the same file are handled correctly."""
        # Create chunk 0001 with multiple ranges
        runner.invoke(
            cli,
            ["chunk", "start", "older", "--project-dir", str(temp_project)]
        )
        chunk1_path = temp_project / "docs" / "chunks" / "0001-older"
        write_goal_frontmatter(chunk1_path, "ACTIVE", [
            {"file": "src/main.py", "ranges": [
                {"lines": "10-20"},
                {"lines": "50-60"},
            ]}
        ])

        # Create chunk 0002 with reference between those ranges
        # 30 <= 60 (older's latest), so it overlaps
        runner.invoke(
            cli,
            ["chunk", "start", "newer", "--project-dir", str(temp_project)]
        )
        chunk2_path = temp_project / "docs" / "chunks" / "0002-newer"
        write_goal_frontmatter(chunk2_path, "ACTIVE", [
            {"file": "src/main.py", "ranges": [{"lines": "30-40"}]}
        ])

        result = runner.invoke(
            cli,
            ["chunk", "overlap", "0002", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/chunks/0001-older" in result.output
