# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/scheduler_decompose - Tests for extracted review_parsing module
"""Tests for the orchestrator review_parsing module.

These tests verify review phase output parsing and configuration loading.
"""

import pytest
from pathlib import Path

from orchestrator.review_parsing import (
    create_review_feedback_file,
    parse_review_decision,
    load_reviewer_config,
    validate_feedback_addressed,
)
from orchestrator.models import ReviewDecision, ReviewIssue, ReviewResult


class TestCreateReviewFeedbackFile:
    """Tests for create_review_feedback_file function."""

    def test_creates_feedback_file(self, tmp_path):
        """Creates REVIEW_FEEDBACK.md in the chunk directory."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        feedback = ReviewResult(
            decision=ReviewDecision.FEEDBACK,
            summary="Code review feedback summary",
        )

        result_path = create_review_feedback_file(tmp_path, "test_chunk", feedback, 1)

        assert result_path.exists()
        assert result_path == chunk_dir / "REVIEW_FEEDBACK.md"
        content = result_path.read_text()
        assert "**Iteration:** 1" in content
        assert "**Decision:** FEEDBACK" in content
        assert "Code review feedback summary" in content

    def test_includes_issues(self, tmp_path):
        """Includes issue details in the feedback file."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        issues = [
            ReviewIssue(
                location="src/main.py:42",
                concern="Missing error handling",
                suggestion="Add try/except block",
            ),
            ReviewIssue(
                location="tests/test_main.py",
                concern="No test coverage for edge case",
                suggestion=None,
            ),
        ]
        feedback = ReviewResult(
            decision=ReviewDecision.FEEDBACK,
            summary="Multiple issues found",
            issues=issues,
        )

        result_path = create_review_feedback_file(tmp_path, "test_chunk", feedback, 2)

        content = result_path.read_text()
        assert "## Issues to Address" in content
        assert "### Issue 1: src/main.py:42" in content
        assert "**Concern:** Missing error handling" in content
        assert "**Suggestion:** Add try/except block" in content
        assert "### Issue 2: tests/test_main.py" in content


class TestParseReviewDecision:
    """Tests for parse_review_decision function."""

    def test_parses_yaml_block(self):
        """Parses YAML decision block from agent output."""
        output = """
Some agent output here...

```yaml
decision: APPROVE
summary: Code looks good, all tests pass
```

More output...
"""
        result = parse_review_decision(output)

        assert result is not None
        assert result.decision == ReviewDecision.APPROVE
        assert result.summary == "Code looks good, all tests pass"

    def test_parses_feedback_with_issues(self):
        """Parses FEEDBACK decision with issues list."""
        output = """
```yaml
decision: FEEDBACK
summary: Some improvements needed
issues:
  - location: src/foo.py
    concern: Type hints missing
    suggestion: Add type annotations
  - location: tests/
    concern: Low coverage
```
"""
        result = parse_review_decision(output)

        assert result is not None
        assert result.decision == ReviewDecision.FEEDBACK
        assert len(result.issues) == 2
        assert result.issues[0].location == "src/foo.py"
        assert result.issues[0].concern == "Type hints missing"
        assert result.issues[0].suggestion == "Add type annotations"
        assert result.issues[1].suggestion is None

    def test_parses_escalate_with_reason(self):
        """Parses ESCALATE decision with reason."""
        output = """
```yaml
decision: ESCALATE
summary: Cannot proceed
reason: Requirements are unclear
```
"""
        result = parse_review_decision(output)

        assert result is not None
        assert result.decision == ReviewDecision.ESCALATE
        assert result.reason == "Requirements are unclear"

    def test_fallback_to_decision_line(self):
        """Falls back to parsing decision: line directly."""
        output = """
After careful review, I've determined:

decision: APPROVE

The code is ready to merge.
"""
        result = parse_review_decision(output)

        assert result is not None
        assert result.decision == ReviewDecision.APPROVE

    def test_case_insensitive_decision(self):
        """Decision parsing is case-insensitive."""
        output = """
```yaml
decision: approve
summary: LGTM
```
"""
        result = parse_review_decision(output)

        assert result is not None
        assert result.decision == ReviewDecision.APPROVE

    def test_returns_none_for_invalid_decision(self):
        """Returns None when decision is invalid."""
        output = """
```yaml
decision: MAYBE
summary: Not sure
```
"""
        result = parse_review_decision(output)

        # Should return None because MAYBE is not a valid decision
        assert result is None

    def test_returns_none_when_no_decision(self):
        """Returns None when no decision can be parsed."""
        output = """
Some agent output without any decision block.
Just regular text here.
"""
        result = parse_review_decision(output)

        assert result is None


class TestLoadReviewerConfig:
    """Tests for load_reviewer_config function."""

    def test_loads_config_from_file(self, tmp_path):
        """Loads reviewer configuration from METADATA.yaml."""
        reviewer_dir = tmp_path / "docs" / "reviewers" / "baseline"
        reviewer_dir.mkdir(parents=True)
        metadata = reviewer_dir / "METADATA.yaml"
        metadata.write_text("""
name: baseline
loop_detection:
  max_iterations: 5
  escalation_threshold: 3
  same_issue_threshold: 4
""")

        config = load_reviewer_config(tmp_path, "baseline")

        assert config["name"] == "baseline"
        assert config["loop_detection"]["max_iterations"] == 5
        assert config["loop_detection"]["escalation_threshold"] == 3
        assert config["loop_detection"]["same_issue_threshold"] == 4

    def test_uses_defaults_when_file_missing(self, tmp_path):
        """Uses default values when config file is missing."""
        config = load_reviewer_config(tmp_path, "nonexistent")

        assert config["loop_detection"]["max_iterations"] == 3
        assert config["loop_detection"]["escalation_threshold"] == 2
        assert config["loop_detection"]["same_issue_threshold"] == 2

    def test_merges_with_defaults(self, tmp_path):
        """Merges partial config with defaults."""
        reviewer_dir = tmp_path / "docs" / "reviewers" / "baseline"
        reviewer_dir.mkdir(parents=True)
        metadata = reviewer_dir / "METADATA.yaml"
        # Only specify max_iterations, others should use defaults
        metadata.write_text("""
name: custom
loop_detection:
  max_iterations: 10
""")

        config = load_reviewer_config(tmp_path, "baseline")

        assert config["name"] == "custom"
        assert config["loop_detection"]["max_iterations"] == 10
        # These should be defaults
        assert config["loop_detection"]["escalation_threshold"] == 2
        assert config["loop_detection"]["same_issue_threshold"] == 2

    def test_default_reviewer_name(self, tmp_path):
        """Uses 'baseline' as default reviewer name."""
        reviewer_dir = tmp_path / "docs" / "reviewers" / "baseline"
        reviewer_dir.mkdir(parents=True)
        metadata = reviewer_dir / "METADATA.yaml"
        metadata.write_text("""
loop_detection:
  max_iterations: 3
""")

        config = load_reviewer_config(tmp_path)  # No reviewer specified

        assert config["loop_detection"]["max_iterations"] == 3


# Chunk: docs/chunks/orch_review_feedback_fidelity - Tests for validate_feedback_addressed
class TestValidateFeedbackAddressed:
    """Tests for validate_feedback_addressed function."""

    def test_returns_true_when_file_deleted(self, tmp_path):
        """Returns True when REVIEW_FEEDBACK.md does not exist (feedback addressed)."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        assert validate_feedback_addressed(tmp_path, "test_chunk") is True

    def test_returns_false_when_file_exists(self, tmp_path):
        """Returns False when REVIEW_FEEDBACK.md still exists (feedback not addressed)."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "REVIEW_FEEDBACK.md").write_text("# Some feedback")

        assert validate_feedback_addressed(tmp_path, "test_chunk") is False

    def test_returns_true_when_chunk_dir_missing(self, tmp_path):
        """Returns True when chunk directory doesn't exist (no feedback to address)."""
        assert validate_feedback_addressed(tmp_path, "nonexistent_chunk") is True
