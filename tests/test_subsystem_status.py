"""Tests for the 've subsystem status' CLI command."""

from ve import cli


# Chunk: docs/chunks/0044-remove_sequence_prefix - Updated for short_name only format
class TestSubsystemStatusDisplay:
    """Tests for 've subsystem status <id>' (display mode)."""

    def test_status_display_shows_current_status(self, runner, temp_project):
        """Show current status for an existing subsystem."""
        # Create a subsystem first
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "validation: DISCOVERING" in result.output

    def test_status_display_with_full_id(self, runner, temp_project):
        """Works with full subsystem directory name."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "validation: DISCOVERING" in result.output

    def test_status_display_with_shortname(self, runner, temp_project):
        """Works with just the shortname."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "validation: DISCOVERING" in result.output


class TestSubsystemStatusTransitions:
    """Tests for valid and invalid status transitions."""

    def test_valid_transition_discovering_to_documented(self, runner, temp_project):
        """DISCOVERING -> DOCUMENTED works."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "validation: DISCOVERING" in result.output
        assert "DOCUMENTED" in result.output

    def test_valid_transition_documented_to_refactoring(self, runner, temp_project):
        """DOCUMENTED -> REFACTORING works."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        # First transition to DOCUMENTED
        runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        # Then to REFACTORING
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "REFACTORING", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "DOCUMENTED" in result.output
        assert "REFACTORING" in result.output

    def test_valid_transition_refactoring_to_stable(self, runner, temp_project):
        """REFACTORING -> STABLE works."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["subsystem", "status", "validation", "REFACTORING", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "STABLE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "REFACTORING" in result.output
        assert "STABLE" in result.output

    def test_valid_transition_stable_to_deprecated(self, runner, temp_project):
        """STABLE -> DEPRECATED works."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["subsystem", "status", "validation", "REFACTORING", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["subsystem", "status", "validation", "STABLE", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DEPRECATED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "STABLE" in result.output
        assert "DEPRECATED" in result.output

    def test_valid_transition_refactoring_to_documented(self, runner, temp_project):
        """REFACTORING -> DOCUMENTED (rollback) works."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["subsystem", "status", "validation", "REFACTORING", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "REFACTORING" in result.output
        assert "DOCUMENTED" in result.output

    def test_invalid_transition_discovering_to_stable(self, runner, temp_project):
        """Cannot skip steps: DISCOVERING -> STABLE fails."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "STABLE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Cannot transition from DISCOVERING to STABLE" in result.output
        assert "Valid transitions:" in result.output

    def test_invalid_transition_deprecated_to_any(self, runner, temp_project):
        """Terminal state enforced: DEPRECATED -> any fails."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DEPRECATED", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Cannot transition from DEPRECATED" in result.output
        assert "terminal state" in result.output


class TestSubsystemStatusIdResolution:
    """Tests for ID resolution (shortname vs full ID)."""

    def test_resolves_shortname_to_full_id(self, runner, temp_project):
        """'validation' resolves to 'validation' directory."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "validation:" in result.output

    def test_accepts_full_id_directly(self, runner, temp_project):
        """'validation' works directly."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "validation:" in result.output


class TestSubsystemStatusErrors:
    """Tests for error handling."""

    def test_subsystem_not_found_error(self, runner, temp_project):
        """Clear error message when subsystem doesn't exist."""
        result = runner.invoke(
            cli,
            ["subsystem", "status", "nonexistent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Subsystem 'nonexistent' not found" in result.output

    def test_invalid_status_value_error(self, runner, temp_project):
        """Lists valid statuses when invalid status provided."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "FOO", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Invalid status 'FOO'" in result.output
        assert "DISCOVERING" in result.output
        assert "DOCUMENTED" in result.output

    def test_invalid_transition_error(self, runner, temp_project):
        """Shows current status and valid next states on invalid transition."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "STABLE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Cannot transition from DISCOVERING to STABLE" in result.output
        assert "Valid transitions:" in result.output


class TestSubsystemStatusOutput:
    """Tests for output format."""

    def test_success_output_shows_transition(self, runner, temp_project):
        """Success shows 'validation: DISCOVERING -> DOCUMENTED'."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # The output should show the transition
        assert "validation: DISCOVERING" in result.output
        assert "DOCUMENTED" in result.output


class TestSubsystemStatusFrontmatterPreservation:
    """Tests for frontmatter preservation during updates."""

    def test_update_preserves_other_frontmatter_fields(self, runner, temp_project):
        """chunks and code_references remain intact."""
        import yaml

        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )

        # Manually add some fields to frontmatter
        overview_path = temp_project / "docs" / "subsystems" / "validation" / "OVERVIEW.md"
        content = overview_path.read_text()

        # Add a chunk reference to the frontmatter (be specific to avoid matching proposed_chunks)
        new_content = content.replace(
            "\nchunks: []\n",
            "\nchunks:\n  - chunk_id: '0001-test'\n    relationship: implements\n"
        )
        overview_path.write_text(new_content)

        # Now update the status
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Verify chunks field is preserved
        updated_content = overview_path.read_text()
        assert "0001-test" in updated_content
        assert "implements" in updated_content

    def test_update_preserves_document_content(self, runner, temp_project):
        """Body content remains unchanged."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )

        # Add some content after the frontmatter
        overview_path = temp_project / "docs" / "subsystems" / "validation" / "OVERVIEW.md"
        content = overview_path.read_text()
        content += "\n## Custom Section\n\nThis is custom content.\n"
        overview_path.write_text(content)

        # Update the status
        result = runner.invoke(
            cli,
            ["subsystem", "status", "validation", "DOCUMENTED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Verify content is preserved
        updated_content = overview_path.read_text()
        assert "## Custom Section" in updated_content
        assert "This is custom content." in updated_content
