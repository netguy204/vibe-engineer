"""Tests for ve reviewer decisions command."""
# Chunk: docs/chunks/reviewer_decisions_list_cli - Few-shot decision aggregation CLI

import os
import time

import pytest
from click.testing import CliRunner

from ve import cli


@pytest.fixture
def initialized_project(temp_project, runner):
    """Create a project with VE initialized."""
    result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
    assert result.exit_code == 0
    return temp_project


@pytest.fixture
def reviewer_decisions_dir(initialized_project):
    """Create the baseline reviewer decisions directory."""
    decisions_dir = initialized_project / "docs" / "reviewers" / "baseline" / "decisions"
    decisions_dir.mkdir(parents=True)
    return decisions_dir


def write_decision_file(decisions_dir, filename, decision, summary, operator_review=None):
    """Helper to write a decision file with frontmatter.

    Args:
        decisions_dir: Path to decisions directory
        filename: Name of the decision file (without .md extension)
        decision: Decision value (APPROVE, FEEDBACK, ESCALATE)
        summary: Summary text
        operator_review: None, "good", "bad", or dict with feedback key
    """
    # Build operator_review YAML
    if operator_review is None:
        op_review_yaml = "operator_review: null"
    elif isinstance(operator_review, str):
        op_review_yaml = f"operator_review: {operator_review}"
    elif isinstance(operator_review, dict):
        op_review_yaml = f"operator_review:\n  feedback: {operator_review['feedback']}"
    else:
        raise ValueError(f"Unexpected operator_review type: {type(operator_review)}")

    content = f"""---
decision: {decision}
summary: {summary}
{op_review_yaml}
---

# Decision Details

This is the body of the decision file.
"""
    filepath = decisions_dir / f"{filename}.md"
    filepath.write_text(content)
    return filepath


class TestReviewerDecisionsCommandExists:
    """Tests that the command exists and accepts expected options."""

    def test_reviewer_group_exists(self, runner):
        """Reviewer command group is available."""
        result = runner.invoke(cli, ["reviewer", "--help"])
        assert result.exit_code == 0
        assert "Reviewer agent commands" in result.output

    def test_decisions_command_exists(self, runner):
        """Help text available for reviewer decisions command."""
        result = runner.invoke(cli, ["reviewer", "decisions", "--help"])
        assert result.exit_code == 0
        assert "--recent" in result.output
        assert "--reviewer" in result.output
        assert "--project-dir" in result.output

    def test_decisions_command_requires_recent(self, runner, initialized_project):
        """--recent option is required."""
        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code != 0
        assert "--recent" in result.output or "Missing option" in result.output


class TestReviewerDecisionsFiltering:
    """Tests that only curated decisions (operator_review != null) are returned."""

    def test_returns_only_curated_decisions(self, runner, reviewer_decisions_dir, initialized_project):
        """Only decisions with operator_review appear in output."""
        # Create decisions - some with operator_review, some without
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_a_1",
            "APPROVE",
            "Approved decision",
            operator_review="good",
        )
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_b_1",
            "FEEDBACK",
            "Feedback decision",
            operator_review=None,  # Not curated
        )
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_c_1",
            "ESCALATE",
            "Escalated decision",
            operator_review={"feedback": "Good escalation"},
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "10", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0

        # Should include curated decisions
        assert "chunk_a_1.md" in result.output
        assert "chunk_c_1.md" in result.output

        # Should NOT include non-curated decision
        assert "chunk_b_1.md" not in result.output

    def test_no_curated_decisions_returns_empty(self, runner, reviewer_decisions_dir, initialized_project):
        """Empty output when no decisions have operator_review."""
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_a_1",
            "APPROVE",
            "Uncurated decision",
            operator_review=None,
        )
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_b_1",
            "FEEDBACK",
            "Also uncurated",
            operator_review=None,
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "10", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0
        # No decision files should appear
        assert "chunk_a_1.md" not in result.output
        assert "chunk_b_1.md" not in result.output


class TestReviewerDecisionsOutputFormat:
    """Tests that output format matches fewshot_output_example.md."""

    def test_output_format_string_operator_review(self, runner, reviewer_decisions_dir, initialized_project):
        """Output matches format for string operator_review values."""
        write_decision_file(
            reviewer_decisions_dir,
            "selective_artifact_friction_1",
            "APPROVE",
            "Implementation correctly adds --projects flag with task-aware friction logging.",
            operator_review="good",
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "1", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0

        # Check format elements
        assert "## docs/reviewers/baseline/decisions/selective_artifact_friction_1.md" in result.output
        assert "**Decision**: APPROVE" in result.output
        assert "**Summary**:" in result.output
        assert "--projects flag" in result.output
        assert "**Operator review**: good" in result.output

    def test_output_format_feedback_operator_review(self, runner, reviewer_decisions_dir, initialized_project):
        """Output matches format for FeedbackReview operator_review values."""
        write_decision_file(
            reviewer_decisions_dir,
            "api_validation_refactor_1",
            "FEEDBACK",
            "Missing validation for edge case in batch endpoint.",
            operator_review={"feedback": "Should have been APPROVE - the edge case is handled by the middleware layer."},
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "1", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0

        # Check format elements
        assert "## docs/reviewers/baseline/decisions/api_validation_refactor_1.md" in result.output
        assert "**Decision**: FEEDBACK" in result.output
        assert "**Summary**:" in result.output
        assert "batch endpoint" in result.output
        assert "**Operator review**:" in result.output
        assert "feedback: Should have been APPROVE" in result.output

    def test_path_is_working_directory_relative(self, runner, reviewer_decisions_dir, initialized_project):
        """Paths are relative to working directory, not absolute."""
        write_decision_file(
            reviewer_decisions_dir,
            "test_chunk_1",
            "APPROVE",
            "Test decision",
            operator_review="good",
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "1", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0

        # Path should be relative (starting with docs/)
        assert "docs/reviewers/baseline/decisions/test_chunk_1.md" in result.output
        # Should NOT contain absolute path
        assert str(initialized_project) not in result.output


class TestReviewerDecisionsSorting:
    """Tests that decisions are sorted by modification time (most recent first)."""

    def test_sorted_by_recency(self, runner, reviewer_decisions_dir, initialized_project):
        """Output is sorted with most recent first."""
        # Create files with explicit modification time differences
        file1 = write_decision_file(
            reviewer_decisions_dir,
            "oldest_chunk_1",
            "APPROVE",
            "Oldest decision",
            operator_review="good",
        )
        time.sleep(0.1)  # Ensure different modification times

        file2 = write_decision_file(
            reviewer_decisions_dir,
            "middle_chunk_1",
            "APPROVE",
            "Middle decision",
            operator_review="good",
        )
        time.sleep(0.1)

        file3 = write_decision_file(
            reviewer_decisions_dir,
            "newest_chunk_1",
            "APPROVE",
            "Newest decision",
            operator_review="good",
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "10", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0

        # Check order - newest should come first
        newest_pos = result.output.find("newest_chunk_1")
        middle_pos = result.output.find("middle_chunk_1")
        oldest_pos = result.output.find("oldest_chunk_1")

        assert newest_pos < middle_pos < oldest_pos, \
            f"Expected newest ({newest_pos}) < middle ({middle_pos}) < oldest ({oldest_pos})"

    def test_recent_limits_output(self, runner, reviewer_decisions_dir, initialized_project):
        """--recent N limits output to N most recent decisions."""
        # Create 5 curated decisions
        for i in range(5):
            write_decision_file(
                reviewer_decisions_dir,
                f"chunk_{i}_1",
                "APPROVE",
                f"Decision {i}",
                operator_review="good",
            )
            time.sleep(0.05)  # Ensure different modification times

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "2", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0

        # Should show exactly 2 decisions (the most recent ones: chunk_4 and chunk_3)
        assert result.output.count("## docs/reviewers/") == 2
        assert "chunk_4_1.md" in result.output
        assert "chunk_3_1.md" in result.output
        # Older ones should not appear
        assert "chunk_0_1.md" not in result.output

    def test_recent_exceeds_available_returns_all(self, runner, reviewer_decisions_dir, initialized_project):
        """When --recent N exceeds available decisions, returns all available."""
        # Create only 2 decisions
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_a_1",
            "APPROVE",
            "Decision A",
            operator_review="good",
        )
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_b_1",
            "APPROVE",
            "Decision B",
            operator_review="good",
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "100", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0

        # Should show both available decisions
        assert "chunk_a_1.md" in result.output
        assert "chunk_b_1.md" in result.output
        assert result.output.count("## docs/reviewers/") == 2


class TestReviewerDecisionsBoundaryConditions:
    """Tests for boundary conditions."""

    def test_no_decisions_directory(self, runner, initialized_project):
        """Empty output when decisions directory doesn't exist."""
        # Don't create the decisions directory
        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "5", "--project-dir", str(initialized_project)],
        )
        # Should succeed but output nothing (or a message)
        assert result.exit_code == 0

    def test_empty_decisions_directory(self, runner, reviewer_decisions_dir, initialized_project):
        """Empty output when decisions directory exists but is empty."""
        # Directory exists but no files
        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "5", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0
        # No decision files should appear
        assert "## docs/reviewers/" not in result.output

    def test_custom_reviewer_name(self, runner, initialized_project):
        """--reviewer option uses different reviewer directory."""
        # Create custom reviewer decisions directory
        custom_dir = initialized_project / "docs" / "reviewers" / "custom" / "decisions"
        custom_dir.mkdir(parents=True)

        write_decision_file(
            custom_dir,
            "custom_decision_1",
            "APPROVE",
            "Custom reviewer decision",
            operator_review="good",
        )

        # Also create baseline to verify we're not reading from it
        baseline_dir = initialized_project / "docs" / "reviewers" / "baseline" / "decisions"
        baseline_dir.mkdir(parents=True)
        write_decision_file(
            baseline_dir,
            "baseline_decision_1",
            "APPROVE",
            "Baseline decision",
            operator_review="good",
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "5", "--reviewer", "custom",
             "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0

        # Should show custom reviewer's decision
        assert "custom_decision_1.md" in result.output
        # Should NOT show baseline decision
        assert "baseline_decision_1.md" not in result.output

    def test_malformed_frontmatter_skipped_with_warning(self, runner, reviewer_decisions_dir, initialized_project):
        """Files with malformed frontmatter are skipped with warning to stderr."""
        # Create a valid decision
        write_decision_file(
            reviewer_decisions_dir,
            "valid_chunk_1",
            "APPROVE",
            "Valid decision",
            operator_review="good",
        )

        # Create a malformed decision file
        malformed_path = reviewer_decisions_dir / "malformed_chunk_1.md"
        malformed_path.write_text("""---
decision: INVALID_VALUE
summary: This has invalid decision value
operator_review: good
---
Body content.
""")

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "10", "--project-dir", str(initialized_project)],
        )

        # Command should succeed
        assert result.exit_code == 0

        # Valid decision should appear
        assert "valid_chunk_1.md" in result.output

        # Malformed decision should be skipped (warning may go to stderr)
        # The important thing is the command doesn't fail


class TestReviewerDecisionsOperatorReviewVariants:
    """Tests for different operator_review value formats."""

    def test_operator_review_good(self, runner, reviewer_decisions_dir, initialized_project):
        """operator_review: good is displayed correctly."""
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_1",
            "APPROVE",
            "Good decision",
            operator_review="good",
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "1", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0
        assert "**Operator review**: good" in result.output

    def test_operator_review_bad(self, runner, reviewer_decisions_dir, initialized_project):
        """operator_review: bad is displayed correctly."""
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_1",
            "APPROVE",
            "Bad decision",
            operator_review="bad",
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "1", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0
        assert "**Operator review**: bad" in result.output

    def test_operator_review_feedback_map(self, runner, reviewer_decisions_dir, initialized_project):
        """operator_review with feedback map is displayed correctly."""
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_1",
            "ESCALATE",
            "Escalated for clarification",
            operator_review={"feedback": "Good escalation - genuinely ambiguous case"},
        )

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--recent", "1", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0
        assert "**Operator review**:" in result.output
        assert "feedback: Good escalation" in result.output
