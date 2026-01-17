"""Tests for the 've narrative list' CLI command.

# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

NOTE: These tests are for the OBSOLETE in-repo narrative behavior.
As of docs/chunks/scratchpad_narrative_commands, narrative commands now use
scratchpad storage (~/.vibe/scratchpad/) instead of in-repo docs/narratives/.

See tests/test_narrative_scratchpad.py for the current behavior tests.
"""

import pytest

from ve import cli

# Skip all tests in this file - they test obsolete in-repo behavior
pytestmark = pytest.mark.skip(
    reason="Obsolete: narrative commands now use scratchpad storage. "
    "See tests/test_narrative_scratchpad.py"
)


class TestNarrativeListCommand:
    """Tests for 've narrative list' CLI command."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["narrative", "list", "--help"])
        assert result.exit_code == 0
        assert "List" in result.output or "list" in result.output.lower()

    def test_empty_project_exits_with_error(self, runner, temp_project):
        """Empty project: stderr says 'No narratives found', exit code 1."""
        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "No narratives found" in result.output

    def test_single_narrative_outputs_path_with_status(self, runner, temp_project):
        """Single narrative: outputs relative path with status, exit code 0."""
        # Create a narrative first
        runner.invoke(
            cli,
            ["narrative", "create", "test_feature", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/narratives/test_feature" in result.output
        assert "[DRAFTING]" in result.output

    def test_multiple_narratives_in_causal_order(self, runner, temp_project):
        """Multiple narratives: outputs in causal order (newest first), exit code 0."""
        # Create narratives
        runner.invoke(
            cli,
            ["narrative", "create", "first", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["narrative", "create", "second", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 2
        # Should be in reverse causal order (newest first)
        assert "second" in lines[0]
        assert "first" in lines[1]

    def test_project_dir_option_works(self, runner, temp_project):
        """--project-dir option works correctly."""
        # Create a narrative in a specific directory
        runner.invoke(
            cli,
            ["narrative", "create", "feature", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/narratives/feature" in result.output

    def test_format_includes_status_brackets(self, runner, temp_project):
        """Status appears in brackets after the path."""
        runner.invoke(
            cli,
            ["narrative", "create", "feature", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Format should be: docs/narratives/feature [DRAFTING]
        assert "docs/narratives/feature [DRAFTING]" in result.output


class TestNarrativeListTipIndicator:
    """Tests for tip indicator in narrative list output."""

    def test_tip_indicator_appears_for_tip_narratives(self, runner, temp_project):
        """Tip indicator (*) appears for ACTIVE narratives with no dependents.

        Note: DRAFTING narratives are not considered tips (they're not "active" yet).
        Only ACTIVE narratives can be tips.
        """
        # Create a narrative first
        runner.invoke(
            cli,
            ["narrative", "create", "standalone", "--project-dir", str(temp_project)]
        )

        # Update the narrative to ACTIVE status so it becomes a tip
        overview_path = temp_project / "docs" / "narratives" / "standalone" / "OVERVIEW.md"
        content = overview_path.read_text()
        content = content.replace("status: DRAFTING", "status: ACTIVE")
        overview_path.write_text(content)

        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # ACTIVE narrative is a tip
        assert "*" in result.output
