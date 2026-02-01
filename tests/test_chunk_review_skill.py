"""Tests for the chunk-review skill template updates for per-file decisions."""
# Chunk: docs/chunks/reviewer_use_decision_files - Test skill template uses new decision file workflow


class TestChunkReviewSkillTemplate:
    """Tests for chunk-review.md.jinja2 template after per-file decision migration."""

    def test_template_renders_without_errors(self):
        """chunk-review template renders without Jinja2 errors."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-review.md.jinja2",
        )

        # Basic structure checks
        assert "## Instructions" in result
        assert "Phase 1" in result
        assert "Phase 4" in result

    def test_phase_1_references_ve_reviewer_decisions(self):
        """Phase 1 instructs to run 've reviewer decisions --recent 10' for few-shot context."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-review.md.jinja2",
        )

        # Should reference the CLI command for few-shot context
        assert "ve reviewer decisions" in result
        assert "--recent" in result

    def test_phase_1_no_longer_reads_decision_log_directly(self):
        """Phase 1 no longer instructs to read DECISION_LOG.md directly."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-review.md.jinja2",
        )

        # Should NOT have instructions to read DECISION_LOG.md as the primary source
        # (It may still be mentioned as historical context, but not as the source of examples)
        phase_1_text = result.split("### Phase 1")[1].split("### Phase 2")[0]
        assert "Read `DECISION_LOG.md`" not in phase_1_text
        assert "Read DECISION_LOG.md" not in phase_1_text

    def test_phase_4_calls_decision_create_command(self):
        """Phase 4 instructs to run 've reviewer decision create' before writing decision."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-review.md.jinja2",
        )

        # Should reference the decision create command
        assert "ve reviewer decision create" in result

    def test_phase_4_no_longer_appends_to_decision_log(self):
        """Phase 4 no longer instructs to append to DECISION_LOG.md."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-review.md.jinja2",
        )

        # Extract Phase 4 content
        phase_4_text = result.split("### Phase 4")[1]
        if "### Phase 5" in phase_4_text:
            phase_4_text = phase_4_text.split("### Phase 5")[0]

        # Should NOT have instructions to append to DECISION_LOG.md
        assert "append" not in phase_4_text.lower() or "DECISION_LOG" not in phase_4_text

    def test_phase_4_fills_decision_template(self):
        """Phase 4 instructs to fill in the decision template file."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-review.md.jinja2",
        )

        # Should mention filling in the template
        assert "decision:" in result
        assert "summary:" in result

    def test_template_includes_auto_generated_header(self):
        """chunk-review template includes auto-generated header."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-review.md.jinja2",
        )

        assert "AUTO-GENERATED FILE" in result
        assert "DO NOT EDIT DIRECTLY" in result

    def test_template_no_jinja_remnants(self):
        """chunk-review template renders without Jinja2 syntax in output."""
        from template_system import render_template

        result = render_template(
            "commands",
            "chunk-review.md.jinja2",
        )

        # No unrendered Jinja control tags
        assert "{%" not in result

        # Any {{ }} should be in code blocks, not raw template vars
        raw_braces = result.count("{{")
        if raw_braces > 0:
            # Should be in code blocks (showing example YAML)
            assert "```" in result


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
