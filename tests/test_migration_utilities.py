"""Tests for the causal ordering migration utilities.

# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

These tests verify the migration script's core functionality:
- Short name extraction from directory names
- Sequence number extraction
- Frontmatter parsing and preservation
"""

import tempfile
from pathlib import Path

import pytest

# Import from the chunk's migration script
import sys

sys.path.insert(
    0, str(Path(__file__).parent.parent / "docs/archive/chunks/causal_ordering_migration")
)
from migrate import (
    extract_sequence_number,
    extract_short_name,
    migrate_artifact_type,
    parse_frontmatter,
    update_frontmatter,
)


class TestExtractShortName:
    """Tests for extract_short_name function."""

    def test_standard_format(self):
        """Standard NNNN-short_name format."""
        assert extract_short_name("0001-short_name") == "short_name"
        assert extract_short_name("0042-my_feature") == "my_feature"

    def test_ticket_suffix_ve_format(self):
        """Ticket suffix with -ve-NNN format is stripped."""
        assert extract_short_name("0001-short_name-ve-001") == "short_name"
        assert extract_short_name("0042-my_feature-ve-123") == "my_feature"

    def test_ticket_suffix_ticket_format(self):
        """Ticket suffix with -ticketNNN format is stripped."""
        assert extract_short_name("0001-short_name-ticket123") == "short_name"

    def test_no_prefix(self):
        """Directory without NNNN- prefix returns as-is."""
        assert extract_short_name("just_a_name") == "just_a_name"

    def test_hyphenated_short_name(self):
        """Short names with hyphens are preserved."""
        assert extract_short_name("0001-my-feature-name") == "my-feature-name"


class TestExtractSequenceNumber:
    """Tests for extract_sequence_number function."""

    def test_standard_format(self):
        """Standard NNNN- prefix."""
        assert extract_sequence_number("0001-foo") == 1
        assert extract_sequence_number("0042-bar") == 42
        assert extract_sequence_number("0999-baz") == 999

    def test_no_prefix(self):
        """No prefix returns 0."""
        assert extract_sequence_number("no_prefix") == 0
        assert extract_sequence_number("foo-bar") == 0

    def test_leading_zeros(self):
        """Leading zeros in sequence number are handled."""
        assert extract_sequence_number("0001-foo") == 1
        assert extract_sequence_number("0100-foo") == 100


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_parses_frontmatter(self):
        """Parses YAML frontmatter correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """---
status: ACTIVE
ticket: null
created_after: ["foo"]
---

# Content
"""
            )
            f.flush()
            path = Path(f.name)

        try:
            fm, yaml_text, rest = parse_frontmatter(path)
            assert fm is not None
            assert fm["status"] == "ACTIVE"
            assert fm["created_after"] == ["foo"]
            assert "# Content" in rest
        finally:
            path.unlink()

    def test_no_frontmatter(self):
        """Handles files without frontmatter."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Just content\n")
            f.flush()
            path = Path(f.name)

        try:
            fm, yaml_text, rest = parse_frontmatter(path)
            assert fm is None
            assert "# Just content" in rest
        finally:
            path.unlink()


class TestUpdateFrontmatter:
    """Tests for update_frontmatter function."""

    def test_updates_existing_created_after(self):
        """Updates existing created_after field."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """---
status: ACTIVE
created_after: ["old_value"]
---

# Content
"""
            )
            f.flush()
            path = Path(f.name)

        try:
            result = update_frontmatter(path, ["new_value"])
            assert result is True

            content = path.read_text()
            assert '["new_value"]' in content
            assert "old_value" not in content
            assert "# Content" in content
        finally:
            path.unlink()

    def test_adds_created_after_when_missing(self):
        """Adds created_after field when not present."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """---
status: ACTIVE
ticket: null
---

# Content
"""
            )
            f.flush()
            path = Path(f.name)

        try:
            result = update_frontmatter(path, ["new_value"])
            assert result is True

            content = path.read_text()
            assert "created_after:" in content
            assert '["new_value"]' in content
            assert "status: ACTIVE" in content
            assert "# Content" in content
        finally:
            path.unlink()

    def test_preserves_other_fields(self):
        """Preserves all other frontmatter fields."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """---
status: IMPLEMENTING
ticket: ve-001
parent_chunk: null
code_paths:
  - src/foo.py
created_after: []
---

# Content
"""
            )
            f.flush()
            path = Path(f.name)

        try:
            result = update_frontmatter(path, ["previous_chunk"])
            assert result is True

            content = path.read_text()
            assert "status: IMPLEMENTING" in content
            assert "ticket: ve-001" in content
            assert "src/foo.py" in content
            assert '["previous_chunk"]' in content
        finally:
            path.unlink()

    def test_empty_created_after(self):
        """Sets empty list for first artifact."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """---
status: ACTIVE
---

# Content
"""
            )
            f.flush()
            path = Path(f.name)

        try:
            result = update_frontmatter(path, [])
            assert result is True

            content = path.read_text()
            assert "created_after: []" in content
        finally:
            path.unlink()


class TestMigrateArtifactType:
    """Tests for migrate_artifact_type function."""

    def test_creates_linear_chain(self):
        """Creates linear chain of created_after references using full directory names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create mock artifacts
            for i, name in enumerate(
                ["0001-first", "0002-second", "0003-third"], start=1
            ):
                (tmppath / name).mkdir()
                (tmppath / name / "GOAL.md").write_text(
                    """---
status: ACTIVE
---

# Content
"""
                )

            # Run migration
            actions = migrate_artifact_type(tmppath, "GOAL.md")

            assert len(actions) == 3
            assert actions[0]["after"] == []  # First has no predecessor
            # Uses full directory names, not short names
            assert actions[1]["after"] == ["0001-first"]
            assert actions[2]["after"] == ["0002-second"]

    def test_handles_ticket_suffixes(self):
        """Correctly extracts short names but uses full directory names for created_after."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create mock artifacts with ticket suffixes
            (tmppath / "0001-feat_one-ve-001").mkdir()
            (tmppath / "0001-feat_one-ve-001" / "GOAL.md").write_text(
                "---\nstatus: ACTIVE\n---\n"
            )

            (tmppath / "0002-feat_two").mkdir()
            (tmppath / "0002-feat_two" / "GOAL.md").write_text(
                "---\nstatus: ACTIVE\n---\n"
            )

            actions = migrate_artifact_type(tmppath, "GOAL.md")

            assert len(actions) == 2
            assert actions[0]["short"] == "feat_one"
            assert actions[1]["short"] == "feat_two"
            # Uses full directory name, not short name
            assert actions[1]["after"] == ["0001-feat_one-ve-001"]

    def test_dry_run_does_not_modify(self):
        """Dry run returns plan but doesn't modify files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            (tmppath / "0001-first").mkdir()
            original = """---
status: ACTIVE
---

# Content
"""
            (tmppath / "0001-first" / "GOAL.md").write_text(original)

            (tmppath / "0002-second").mkdir()
            (tmppath / "0002-second" / "GOAL.md").write_text(original)

            # Dry run
            actions = migrate_artifact_type(tmppath, "GOAL.md", dry_run=True)

            assert len(actions) == 2

            # Files should be unchanged
            assert (tmppath / "0001-first" / "GOAL.md").read_text() == original
            assert (tmppath / "0002-second" / "GOAL.md").read_text() == original

    def test_skips_directories_without_main_file(self):
        """Skips directories that don't have the main file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Valid artifact
            (tmppath / "0001-first").mkdir()
            (tmppath / "0001-first" / "GOAL.md").write_text(
                "---\nstatus: ACTIVE\n---\n"
            )

            # Directory without GOAL.md
            (tmppath / "0002-incomplete").mkdir()

            actions = migrate_artifact_type(tmppath, "GOAL.md")

            assert len(actions) == 1
            assert actions[0]["dir"] == "0001-first"
