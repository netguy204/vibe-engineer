"""Tests for DECISION_LOG.md migration to individual decision files."""
# Chunk: docs/chunks/reviewer_use_decision_files - Migration tests for per-file decision system

import pathlib
import yaml

import pytest


# Sample DECISION_LOG.md entry format
SAMPLE_ENTRY = """## my_feature - 2026-01-31 12:30

**Mode:** final
**Iteration:** 1
**Decision:** APPROVE

### Context Summary
- Goal: Add a new feature to the system
- Linked artifacts: None

### Assessment
The implementation is complete and correct.

### Decision Rationale
All success criteria are met.

### Example Quality
- [ ] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---
"""

SAMPLE_ENTRY_WITH_GOOD = """## another_chunk - 2026-01-31 14:00

**Mode:** final
**Iteration:** 1
**Decision:** APPROVE

### Context Summary
- Goal: Add another feature
- Linked artifacts: investigation: some_investigation

### Assessment
Implementation follows best practices.

### Decision Rationale
Code quality is excellent.

### Example Quality
- [x] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---
"""

SAMPLE_ENTRY_WITH_BAD = """## bad_chunk - 2026-01-31 15:00

**Mode:** final
**Iteration:** 2
**Decision:** FEEDBACK

### Context Summary
- Goal: Fix a bug
- Linked artifacts: None

### Assessment
Missing test coverage.

### Decision Rationale
Tests are required.

### Example Quality
- [ ] Good example (incorporate into future reviews)
- [x] Bad example (avoid this pattern)
- [ ] Feedback: _______________

---
"""

SAMPLE_ENTRY_WITH_FEEDBACK = """## feedback_chunk - 2026-01-31 16:00

**Mode:** final
**Iteration:** 1
**Decision:** ESCALATE

### Context Summary
- Goal: Refactor authentication
- Linked artifacts: narrative: auth_refactor

### Assessment
Needs operator decision on approach.

### Decision Rationale
Architectural uncertainty.

### Example Quality
- [ ] Good example (incorporate into future reviews)
- [ ] Bad example (avoid this pattern)
- [x] Feedback: The escalation was appropriate given the complexity

---
"""


class TestParseDecisionLogEntry:
    """Tests for parsing DECISION_LOG.md entry format."""

    def test_extracts_chunk_name_from_header(self):
        """Parser extracts chunk name from entry header."""
        from decision_migration import parse_entry

        entry = parse_entry(SAMPLE_ENTRY)
        assert entry is not None
        assert entry.chunk == "my_feature"

    def test_extracts_date_from_header(self):
        """Parser extracts date from entry header."""
        from decision_migration import parse_entry

        entry = parse_entry(SAMPLE_ENTRY)
        assert entry is not None
        assert entry.date == "2026-01-31 12:30"

    def test_extracts_decision_from_entry(self):
        """Parser extracts decision value from entry."""
        from decision_migration import parse_entry

        entry = parse_entry(SAMPLE_ENTRY)
        assert entry is not None
        assert entry.decision == "APPROVE"

    def test_extracts_iteration_from_entry(self):
        """Parser extracts iteration from entry."""
        from decision_migration import parse_entry

        entry = parse_entry(SAMPLE_ENTRY)
        assert entry is not None
        assert entry.iteration == 1

    def test_extracts_assessment_from_entry(self):
        """Parser extracts assessment content from entry."""
        from decision_migration import parse_entry

        entry = parse_entry(SAMPLE_ENTRY)
        assert entry is not None
        assert "implementation is complete" in entry.assessment.lower()

    def test_extracts_rationale_from_entry(self):
        """Parser extracts decision rationale from entry."""
        from decision_migration import parse_entry

        entry = parse_entry(SAMPLE_ENTRY)
        assert entry is not None
        assert "success criteria" in entry.rationale.lower()


class TestDetectOperatorFeedback:
    """Tests for detecting operator feedback from checkbox markers."""

    def test_no_checkboxes_returns_none(self):
        """Entry with unchecked boxes returns None for operator_review."""
        from decision_migration import parse_entry

        entry = parse_entry(SAMPLE_ENTRY)
        assert entry is not None
        assert entry.operator_review is None

    def test_good_checkbox_returns_good(self):
        """Entry with [x] Good example returns 'good'."""
        from decision_migration import parse_entry

        entry = parse_entry(SAMPLE_ENTRY_WITH_GOOD)
        assert entry is not None
        assert entry.operator_review == "good"

    def test_bad_checkbox_returns_bad(self):
        """Entry with [x] Bad example returns 'bad'."""
        from decision_migration import parse_entry

        entry = parse_entry(SAMPLE_ENTRY_WITH_BAD)
        assert entry is not None
        assert entry.operator_review == "bad"

    def test_feedback_checkbox_returns_feedback_dict(self):
        """Entry with [x] Feedback: message returns feedback dict."""
        from decision_migration import parse_entry

        entry = parse_entry(SAMPLE_ENTRY_WITH_FEEDBACK)
        assert entry is not None
        assert isinstance(entry.operator_review, dict)
        assert "feedback" in entry.operator_review
        assert "appropriate given the complexity" in entry.operator_review["feedback"]

    def test_uppercase_x_is_detected(self):
        """Entry with [X] (uppercase) is detected as checked."""
        from decision_migration import parse_entry

        entry_text = SAMPLE_ENTRY.replace("- [ ] Good example", "- [X] Good example")
        entry = parse_entry(entry_text)
        assert entry is not None
        assert entry.operator_review == "good"


class TestSplitDecisionLog:
    """Tests for splitting DECISION_LOG.md into individual entries."""

    def test_splits_multiple_entries(self):
        """Log with multiple entries is split correctly."""
        from decision_migration import split_log_entries

        log_content = f"""# Decision Log: baseline

This log records all review decisions.

---

{SAMPLE_ENTRY}

{SAMPLE_ENTRY_WITH_GOOD}
"""
        entries = split_log_entries(log_content)
        assert len(entries) == 2

    def test_handles_empty_log(self):
        """Log with no entries returns empty list."""
        from decision_migration import split_log_entries

        log_content = """# Decision Log: baseline

This log records all review decisions.

---
"""
        entries = split_log_entries(log_content)
        assert len(entries) == 0


class TestMigrateDecisionLog:
    """Tests for full migration of DECISION_LOG.md to individual files."""

    def test_creates_decision_files_for_curated_entries(self, temp_project):
        """Migration creates decision files for entries with operator feedback."""
        from decision_migration import migrate_decision_log

        # Create decision log
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        log_content = f"""# Decision Log: baseline

This log records all review decisions.

---

{SAMPLE_ENTRY_WITH_GOOD}

{SAMPLE_ENTRY}
"""
        (reviewers_dir / "DECISION_LOG.md").write_text(log_content)

        # Run migration
        result = migrate_decision_log(temp_project, "baseline")

        # Only curated entry should create a file
        assert result.created == 1
        assert result.skipped == 1

        # Verify file exists
        decision_path = reviewers_dir / "decisions" / "another_chunk_1.md"
        assert decision_path.exists()

    def test_created_file_has_correct_frontmatter(self, temp_project):
        """Migrated file has correct frontmatter with operator_review."""
        from decision_migration import migrate_decision_log

        # Create decision log
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        log_content = f"""# Decision Log: baseline

---

{SAMPLE_ENTRY_WITH_GOOD}
"""
        (reviewers_dir / "DECISION_LOG.md").write_text(log_content)

        migrate_decision_log(temp_project, "baseline")

        # Parse the created file
        decision_path = reviewers_dir / "decisions" / "another_chunk_1.md"
        content = decision_path.read_text()

        # Extract frontmatter
        assert content.startswith("---")
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        assert frontmatter["decision"] == "APPROVE"
        assert frontmatter["operator_review"] == "good"
        assert frontmatter["summary"] is not None

    def test_created_file_has_criteria_assessment_body(self, temp_project):
        """Migrated file has criteria assessment content in body."""
        from decision_migration import migrate_decision_log

        # Create decision log
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        log_content = f"""# Decision Log: baseline

---

{SAMPLE_ENTRY_WITH_GOOD}
"""
        (reviewers_dir / "DECISION_LOG.md").write_text(log_content)

        migrate_decision_log(temp_project, "baseline")

        # Read the created file body
        decision_path = reviewers_dir / "decisions" / "another_chunk_1.md"
        content = decision_path.read_text()

        # Body should contain assessment content
        assert "## Criteria Assessment" in content or "## Assessment" in content
        assert "best practices" in content.lower()

    def test_skips_entries_without_operator_feedback(self, temp_project):
        """Migration skips entries without operator feedback."""
        from decision_migration import migrate_decision_log

        # Create decision log with only uncurated entries
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        log_content = f"""# Decision Log: baseline

---

{SAMPLE_ENTRY}
"""
        (reviewers_dir / "DECISION_LOG.md").write_text(log_content)

        result = migrate_decision_log(temp_project, "baseline")

        assert result.created == 0
        assert result.skipped == 1

        # No decision files created
        decisions_dir = reviewers_dir / "decisions"
        if decisions_dir.exists():
            md_files = list(decisions_dir.glob("*.md"))
            assert len(md_files) == 0

    def test_handles_multiple_iterations_of_same_chunk(self, temp_project):
        """Multiple iterations of same chunk get incrementing iteration numbers."""
        from decision_migration import migrate_decision_log

        # Create entry with iteration 2
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        log_content = f"""# Decision Log: baseline

---

{SAMPLE_ENTRY_WITH_BAD}
"""
        (reviewers_dir / "DECISION_LOG.md").write_text(log_content)

        migrate_decision_log(temp_project, "baseline")

        # File should use the iteration from the entry
        decision_path = reviewers_dir / "decisions" / "bad_chunk_2.md"
        assert decision_path.exists()

    def test_creates_decisions_directory_if_missing(self, temp_project):
        """Migration creates decisions directory if it doesn't exist."""
        from decision_migration import migrate_decision_log

        # Create decision log but not decisions directory
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        log_content = f"""# Decision Log: baseline

---

{SAMPLE_ENTRY_WITH_GOOD}
"""
        (reviewers_dir / "DECISION_LOG.md").write_text(log_content)

        # Verify decisions dir doesn't exist
        decisions_dir = reviewers_dir / "decisions"
        assert not decisions_dir.exists()

        migrate_decision_log(temp_project, "baseline")

        # Now it should exist
        assert decisions_dir.exists()

    def test_feedback_message_preserved_in_migration(self, temp_project):
        """Operator feedback message is preserved in migrated file."""
        from decision_migration import migrate_decision_log

        # Create decision log with feedback entry
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        log_content = f"""# Decision Log: baseline

---

{SAMPLE_ENTRY_WITH_FEEDBACK}
"""
        (reviewers_dir / "DECISION_LOG.md").write_text(log_content)

        migrate_decision_log(temp_project, "baseline")

        # Parse the created file
        decision_path = reviewers_dir / "decisions" / "feedback_chunk_1.md"
        content = decision_path.read_text()

        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        assert isinstance(frontmatter["operator_review"], dict)
        assert "appropriate given the complexity" in frontmatter["operator_review"]["feedback"]


class TestMigrateCLICommand:
    """Tests for 've reviewer migrate-decisions' CLI command."""

    def test_command_exists(self, runner):
        """The migrate-decisions command exists."""
        from ve import cli

        result = runner.invoke(cli, ["reviewer", "migrate-decisions", "--help"])
        assert result.exit_code == 0
        assert "migrate" in result.output.lower()

    def test_reports_migration_count(self, runner, temp_project):
        """Command reports how many decisions were migrated."""
        from ve import cli

        # Create decision log with curated entry
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        log_content = f"""# Decision Log: baseline

---

{SAMPLE_ENTRY_WITH_GOOD}

{SAMPLE_ENTRY}
"""
        (reviewers_dir / "DECISION_LOG.md").write_text(log_content)

        result = runner.invoke(
            cli,
            ["reviewer", "migrate-decisions", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "1" in result.output  # 1 migrated
        assert "another_chunk" in result.output or "created" in result.output.lower()

    def test_accepts_reviewer_flag(self, runner, temp_project):
        """Command accepts --reviewer flag."""
        from ve import cli

        # Create decision log for custom reviewer
        reviewers_dir = temp_project / "docs" / "reviewers" / "custom"
        reviewers_dir.mkdir(parents=True)
        log_content = f"""# Decision Log: custom

---

{SAMPLE_ENTRY_WITH_GOOD}
"""
        (reviewers_dir / "DECISION_LOG.md").write_text(log_content)

        result = runner.invoke(
            cli,
            ["reviewer", "migrate-decisions", "--reviewer", "custom", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # File should be created for custom reviewer
        decision_path = reviewers_dir / "decisions" / "another_chunk_1.md"
        assert decision_path.exists()

    def test_preserves_original_decision_log(self, runner, temp_project):
        """Migration does not delete the original DECISION_LOG.md."""
        from ve import cli

        # Create decision log
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        original_content = f"""# Decision Log: baseline

---

{SAMPLE_ENTRY_WITH_GOOD}
"""
        log_path = reviewers_dir / "DECISION_LOG.md"
        log_path.write_text(original_content)

        runner.invoke(
            cli,
            ["reviewer", "migrate-decisions", "--project-dir", str(temp_project)]
        )

        # Original log should still exist
        assert log_path.exists()
        assert log_path.read_text() == original_content

    def test_handles_missing_decision_log(self, runner, temp_project):
        """Command handles missing DECISION_LOG.md gracefully."""
        from ve import cli

        # Create reviewer dir but no log
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("name: baseline\n")

        result = runner.invoke(
            cli,
            ["reviewer", "migrate-decisions", "--project-dir", str(temp_project)]
        )
        # Should not crash, just report nothing to migrate
        assert result.exit_code == 0
        assert "0" in result.output or "no" in result.output.lower()
