"""Tests for Reviewers domain class."""
# Chunk: docs/chunks/reviewer_decisions_dedup - Tests for list_curated_decisions()

import os
import pathlib
import time

import pytest

from reviewers import CuratedDecision, Reviewers


@pytest.fixture
def project_dir(tmp_path):
    """Create a basic project directory."""
    return tmp_path


@pytest.fixture
def reviewers(project_dir):
    """Create a Reviewers instance for testing."""
    return Reviewers(project_dir)


@pytest.fixture
def reviewer_decisions_dir(project_dir):
    """Create the baseline reviewer decisions directory."""
    decisions_dir = project_dir / "docs" / "reviewers" / "baseline" / "decisions"
    decisions_dir.mkdir(parents=True)
    # Create METADATA.yaml so it's recognized as a reviewer
    (decisions_dir.parent / "METADATA.yaml").write_text("name: baseline\n")
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


class TestListCuratedDecisionsFiltering:
    """Tests that only curated decisions (operator_review != null) are returned."""

    def test_returns_only_curated_decisions(self, reviewers, reviewer_decisions_dir):
        """Only decisions with operator_review are returned."""
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

        results = reviewers.list_curated_decisions("baseline")

        # Should return exactly 2 curated decisions
        assert len(results) == 2
        paths = [r.path.name for r in results]
        assert "chunk_a_1.md" in paths
        assert "chunk_c_1.md" in paths
        assert "chunk_b_1.md" not in paths

    def test_no_curated_decisions_returns_empty(self, reviewers, reviewer_decisions_dir):
        """Empty list when no decisions have operator_review."""
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

        results = reviewers.list_curated_decisions("baseline")

        assert results == []


class TestListCuratedDecisionsSorting:
    """Tests that decisions are sorted by modification time (most recent first)."""

    def test_sorted_by_recency(self, reviewers, reviewer_decisions_dir):
        """Results are sorted with most recent first."""
        # Create files with explicit modification time differences
        write_decision_file(
            reviewer_decisions_dir,
            "oldest_chunk_1",
            "APPROVE",
            "Oldest decision",
            operator_review="good",
        )
        time.sleep(0.1)  # Ensure different modification times

        write_decision_file(
            reviewer_decisions_dir,
            "middle_chunk_1",
            "APPROVE",
            "Middle decision",
            operator_review="good",
        )
        time.sleep(0.1)

        write_decision_file(
            reviewer_decisions_dir,
            "newest_chunk_1",
            "APPROVE",
            "Newest decision",
            operator_review="good",
        )

        results = reviewers.list_curated_decisions("baseline")

        # Check order - newest should come first
        assert len(results) == 3
        assert results[0].path.name == "newest_chunk_1.md"
        assert results[1].path.name == "middle_chunk_1.md"
        assert results[2].path.name == "oldest_chunk_1.md"

    def test_respects_limit(self, reviewers, reviewer_decisions_dir):
        """limit parameter limits output to N most recent decisions."""
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

        results = reviewers.list_curated_decisions("baseline", limit=2)

        # Should return exactly 2 decisions (the most recent ones: chunk_4 and chunk_3)
        assert len(results) == 2
        names = [r.path.name for r in results]
        assert "chunk_4_1.md" in names
        assert "chunk_3_1.md" in names

    def test_limit_exceeds_available_returns_all(self, reviewers, reviewer_decisions_dir):
        """When limit exceeds available decisions, returns all available."""
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

        results = reviewers.list_curated_decisions("baseline", limit=100)

        # Should return both available decisions
        assert len(results) == 2

    def test_limit_none_returns_all(self, reviewers, reviewer_decisions_dir):
        """When limit is None, returns all curated decisions."""
        for i in range(5):
            write_decision_file(
                reviewer_decisions_dir,
                f"chunk_{i}_1",
                "APPROVE",
                f"Decision {i}",
                operator_review="good",
            )

        results = reviewers.list_curated_decisions("baseline", limit=None)

        assert len(results) == 5


class TestListCuratedDecisionsBoundaryConditions:
    """Tests for boundary conditions."""

    def test_no_decisions_directory(self, reviewers, project_dir):
        """Empty list when decisions directory doesn't exist."""
        # Don't create the decisions directory
        results = reviewers.list_curated_decisions("baseline")
        assert results == []

    def test_empty_decisions_directory(self, reviewers, reviewer_decisions_dir):
        """Empty list when decisions directory exists but is empty."""
        # Directory exists but no files
        results = reviewers.list_curated_decisions("baseline")
        assert results == []

    def test_nonexistent_reviewer(self, reviewers, project_dir):
        """Empty list when reviewer doesn't exist."""
        results = reviewers.list_curated_decisions("nonexistent")
        assert results == []

    def test_malformed_frontmatter_skipped(self, reviewers, reviewer_decisions_dir):
        """Files with malformed frontmatter are skipped."""
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

        results = reviewers.list_curated_decisions("baseline")

        # Should return only the valid decision
        assert len(results) == 1
        assert results[0].path.name == "valid_chunk_1.md"


class TestListCuratedDecisionsReturnType:
    """Tests that return type is correct CuratedDecision dataclass."""

    def test_returns_curated_decision_instances(self, reviewers, reviewer_decisions_dir):
        """Results are CuratedDecision instances with correct fields."""
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_1",
            "APPROVE",
            "Test decision",
            operator_review="good",
        )

        results = reviewers.list_curated_decisions("baseline")

        assert len(results) == 1
        result = results[0]

        # Verify it's a CuratedDecision
        assert isinstance(result, CuratedDecision)

        # Verify fields
        assert isinstance(result.path, pathlib.Path)
        assert result.path.name == "chunk_1.md"

        # Verify frontmatter is parsed correctly
        from models import DecisionFrontmatter
        assert isinstance(result.frontmatter, DecisionFrontmatter)
        assert result.frontmatter.decision.value == "APPROVE"
        assert result.frontmatter.summary == "Test decision"
        assert result.frontmatter.operator_review == "good"

        # Verify mtime is set
        assert isinstance(result.mtime, float)
        assert result.mtime > 0

    def test_feedback_review_operator_review(self, reviewers, reviewer_decisions_dir):
        """FeedbackReview operator_review is correctly parsed."""
        write_decision_file(
            reviewer_decisions_dir,
            "chunk_1",
            "FEEDBACK",
            "Feedback decision",
            operator_review={"feedback": "Should have been APPROVE"},
        )

        results = reviewers.list_curated_decisions("baseline")

        assert len(results) == 1
        result = results[0]

        from models import FeedbackReview
        assert isinstance(result.frontmatter.operator_review, FeedbackReview)
        assert result.frontmatter.operator_review.feedback == "Should have been APPROVE"
