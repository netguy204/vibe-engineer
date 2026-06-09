"""Tests for the per-file review decision workflow."""
# Chunk: docs/chunks/reviewer_use_decision_files - Test skill template uses new decision file workflow
# Chunk: docs/chunks/plugin_init_slimdown - Removed chunk-review template rendering tests;
# the command now ships statically with the Claude Code plugin (see tests/test_plugin_commands.py)


class TestConcurrentReviewsNoConflicts:
    """Tests verifying concurrent reviews produce no merge conflicts."""

    def test_concurrent_decisions_create_separate_files(self, temp_project):
        """Two concurrent reviews for different chunks create separate files."""
        # Create two decision files manually (simulating concurrent reviews)
        decisions_dir = temp_project / "docs" / "reviewers" / "baseline" / "decisions"
        decisions_dir.mkdir(parents=True)

        # First review writes its file
        file1 = decisions_dir / "chunk_a_1.md"
        file1.write_text("""---
decision: APPROVE
summary: First chunk approved
operator_review: null
---

## Assessment
""")

        # Second review writes its file (no conflict!)
        file2 = decisions_dir / "chunk_b_1.md"
        file2.write_text("""---
decision: FEEDBACK
summary: Second chunk needs work
operator_review: null
---

## Assessment
""")

        # Both files exist without conflict
        assert file1.exists()
        assert file2.exists()

        # Files have distinct content
        assert "chunk_a" not in file2.read_text()
        assert "chunk_b" not in file1.read_text()

    def test_decision_files_are_independent(self, temp_project):
        """Decision files for different chunks are completely independent."""
        decisions_dir = temp_project / "docs" / "reviewers" / "baseline" / "decisions"
        decisions_dir.mkdir(parents=True)

        # Create files for different chunks
        chunks = ["auth_refactor", "api_cleanup", "test_coverage"]
        for chunk in chunks:
            path = decisions_dir / f"{chunk}_1.md"
            path.write_text(f"---\ndecision: APPROVE\nsummary: {chunk}\n---\n")

        # All files exist and have correct content
        for chunk in chunks:
            path = decisions_dir / f"{chunk}_1.md"
            assert path.exists()
            assert chunk in path.read_text()

        # Modifying one doesn't affect others
        first_file = decisions_dir / "auth_refactor_1.md"
        first_file.write_text("---\ndecision: FEEDBACK\nsummary: modified\n---\n")

        # Other files unchanged
        assert "api_cleanup" in (decisions_dir / "api_cleanup_1.md").read_text()
        assert "test_coverage" in (decisions_dir / "test_coverage_1.md").read_text()
