"""Tests for reviewer decisions review CLI commands."""
# Chunk: docs/chunks/reviewer_decisions_review_cli - CLI for operator decision review

import pytest
from click.testing import CliRunner

from ve import cli


@pytest.fixture
def initialized_project(temp_project, runner):
    """Create a project with reviewer structure initialized."""
    result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
    assert result.exit_code == 0
    return temp_project


@pytest.fixture
def project_with_decision(initialized_project):
    """Create a project with a sample decision file."""
    decisions_dir = initialized_project / "docs" / "reviewers" / "baseline" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)

    decision_file = decisions_dir / "test_chunk_1.md"
    decision_file.write_text("""---
decision: APPROVE
summary: Implementation meets all criteria
operator_review: null
---

## Criteria Assessment

### Criterion 1: Test criterion

- **Status**: satisfied
- **Evidence**: Implementation matches specification
""")
    return initialized_project, decision_file


class TestReviewerDecisionsReviewCommand:
    """Tests for 've reviewer decisions review' command."""

    def test_review_command_exists(self, runner):
        """Help text available for reviewer decisions review command."""
        result = runner.invoke(cli, ["reviewer", "decisions", "review", "--help"])
        assert result.exit_code == 0
        assert "Mark a decision" in result.output or "Review" in result.output or "review" in result.output

    def test_review_good_updates_frontmatter(self, runner, project_with_decision):
        """'ve reviewer decisions review <path> good' marks decision as good."""
        project, decision_file = project_with_decision

        result = runner.invoke(
            cli,
            [
                "reviewer", "decisions", "review",
                "--project-dir", str(project),
                str(decision_file.relative_to(project)),
                "good",
            ],
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify frontmatter was updated
        content = decision_file.read_text()
        assert "operator_review: good" in content

    def test_review_bad_updates_frontmatter(self, runner, project_with_decision):
        """'ve reviewer decisions review <path> bad' marks decision as bad."""
        project, decision_file = project_with_decision

        result = runner.invoke(
            cli,
            [
                "reviewer", "decisions", "review",
                "--project-dir", str(project),
                str(decision_file.relative_to(project)),
                "bad",
            ],
        )
        assert result.exit_code == 0

        # Verify frontmatter was updated
        content = decision_file.read_text()
        assert "operator_review: bad" in content

    def test_review_feedback_updates_frontmatter(self, runner, project_with_decision):
        """'ve reviewer decisions review <path> --feedback "<message>"' sets feedback map."""
        project, decision_file = project_with_decision

        result = runner.invoke(
            cli,
            [
                "reviewer", "decisions", "review",
                "--project-dir", str(project),
                str(decision_file.relative_to(project)),
                "--feedback", "The summary is too verbose",
            ],
        )
        assert result.exit_code == 0

        # Verify frontmatter was updated with feedback map
        content = decision_file.read_text()
        assert "operator_review:" in content
        assert "feedback:" in content
        assert "The summary is too verbose" in content

    def test_review_nonexistent_path_fails(self, runner, initialized_project):
        """Command fails with appropriate error for non-existent path."""
        result = runner.invoke(
            cli,
            [
                "reviewer", "decisions", "review",
                "--project-dir", str(initialized_project),
                "docs/reviewers/baseline/decisions/nonexistent.md",
                "good",
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "does not exist" in result.output.lower()

    def test_review_invalid_path_fails(self, runner, initialized_project):
        """Command fails for path that is not a decision file."""
        # Create a non-decision file
        readme = initialized_project / "README.md"
        readme.write_text("# Test Project\n")

        result = runner.invoke(
            cli,
            [
                "reviewer", "decisions", "review",
                "--project-dir", str(initialized_project),
                "README.md",
                "good",
            ],
        )
        assert result.exit_code != 0
        assert "decision" in result.output.lower() or "invalid" in result.output.lower()

    def test_review_relative_path_works(self, runner, project_with_decision, monkeypatch):
        """Path argument works with working-directory-relative paths."""
        project, decision_file = project_with_decision

        # Change working directory to project
        monkeypatch.chdir(project)

        result = runner.invoke(
            cli,
            [
                "reviewer", "decisions", "review",
                str(decision_file.relative_to(project)),
                "good",
            ],
        )
        assert result.exit_code == 0

        # Verify frontmatter was updated
        content = decision_file.read_text()
        assert "operator_review: good" in content

    def test_review_outputs_confirmation(self, runner, project_with_decision):
        """Command outputs confirmation message."""
        project, decision_file = project_with_decision

        result = runner.invoke(
            cli,
            [
                "reviewer", "decisions", "review",
                "--project-dir", str(project),
                str(decision_file.relative_to(project)),
                "good",
            ],
        )
        assert result.exit_code == 0
        assert "good" in result.output.lower() or "updated" in result.output.lower()

    def test_review_verdict_and_feedback_mutually_exclusive(self, runner, project_with_decision):
        """Cannot specify both verdict (good/bad) and --feedback."""
        project, decision_file = project_with_decision

        result = runner.invoke(
            cli,
            [
                "reviewer", "decisions", "review",
                "--project-dir", str(project),
                str(decision_file.relative_to(project)),
                "good",
                "--feedback", "Some feedback",
            ],
        )
        assert result.exit_code != 0
        # Should fail because specifying both verdict and feedback is not allowed


class TestReviewerDecisionsPendingFlag:
    """Tests for 've reviewer decisions --pending' flag."""

    def test_pending_flag_exists(self, runner):
        """Help text shows --pending option."""
        result = runner.invoke(cli, ["reviewer", "decisions", "--help"])
        assert result.exit_code == 0
        assert "--pending" in result.output

    def test_pending_lists_null_operator_review(self, runner, initialized_project):
        """'--pending' lists only decisions with null operator_review."""
        decisions_dir = initialized_project / "docs" / "reviewers" / "baseline" / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)

        # Create a pending decision (operator_review: null)
        pending = decisions_dir / "pending_chunk_1.md"
        pending.write_text("""---
decision: APPROVE
summary: Pending review
operator_review: null
---

## Criteria Assessment
""")

        # Create a reviewed decision (operator_review: good)
        reviewed = decisions_dir / "reviewed_chunk_1.md"
        reviewed.write_text("""---
decision: APPROVE
summary: Already reviewed
operator_review: good
---

## Criteria Assessment
""")

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--pending", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0
        assert "pending_chunk_1" in result.output
        assert "reviewed_chunk_1" not in result.output

    def test_pending_excludes_good_bad_feedback(self, runner, initialized_project):
        """'--pending' excludes decisions marked 'good', 'bad', or with feedback."""
        decisions_dir = initialized_project / "docs" / "reviewers" / "baseline" / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)

        # Create decisions with various operator_review values
        (decisions_dir / "pending_1.md").write_text("""---
decision: APPROVE
summary: Pending
operator_review: null
---
""")
        (decisions_dir / "good_1.md").write_text("""---
decision: APPROVE
summary: Good
operator_review: good
---
""")
        (decisions_dir / "bad_1.md").write_text("""---
decision: FEEDBACK
summary: Bad
operator_review: bad
---
""")
        (decisions_dir / "feedback_1.md").write_text("""---
decision: ESCALATE
summary: Has feedback
operator_review:
  feedback: Needs more detail
---
""")

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--pending", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0
        assert "pending_1" in result.output
        assert "good_1" not in result.output
        assert "bad_1" not in result.output
        assert "feedback_1" not in result.output

    def test_pending_no_pending_decisions(self, runner, initialized_project):
        """'--pending' with no pending decisions outputs appropriate message."""
        decisions_dir = initialized_project / "docs" / "reviewers" / "baseline" / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)

        # Create only reviewed decisions
        (decisions_dir / "reviewed_1.md").write_text("""---
decision: APPROVE
summary: Already reviewed
operator_review: good
---
""")

        result = runner.invoke(
            cli,
            ["reviewer", "decisions", "--pending", "--project-dir", str(initialized_project)],
        )
        assert result.exit_code == 0
        assert "no pending" in result.output.lower() or "0" in result.output

    def test_pending_with_reviewer_filter(self, runner, initialized_project):
        """'--pending' combined with '--reviewer' filters by reviewer."""
        # Create decisions for different reviewers
        baseline_dir = initialized_project / "docs" / "reviewers" / "baseline" / "decisions"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        (baseline_dir / "baseline_pending.md").write_text("""---
decision: APPROVE
summary: Baseline pending
operator_review: null
---
""")

        other_dir = initialized_project / "docs" / "reviewers" / "other" / "decisions"
        other_dir.mkdir(parents=True, exist_ok=True)
        (other_dir / "other_pending.md").write_text("""---
decision: APPROVE
summary: Other pending
operator_review: null
---
""")
        # Also need METADATA.yaml for "other" reviewer
        (initialized_project / "docs" / "reviewers" / "other" / "METADATA.yaml").write_text("""name: other
trust_level: observation
""")

        result = runner.invoke(
            cli,
            [
                "reviewer", "decisions",
                "--pending",
                "--reviewer", "baseline",
                "--project-dir", str(initialized_project),
            ],
        )
        assert result.exit_code == 0
        assert "baseline_pending" in result.output
        assert "other_pending" not in result.output
