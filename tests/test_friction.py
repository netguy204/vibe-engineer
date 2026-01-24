"""Tests for friction module business logic."""
# Subsystem: docs/subsystems/friction_tracking - Friction log management
# Chunk: docs/chunks/friction_template_and_cli - Friction log business logic

import pytest

from friction import Friction, FrictionEntry, FrictionStatus


class TestFrictionParseFrontmatter:
    """Tests for Friction.parse_frontmatter method."""

    def test_parse_frontmatter_empty(self, temp_project):
        """New friction log with empty arrays parses correctly."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log
""")
        friction = Friction(temp_project)
        frontmatter = friction.parse_frontmatter()

        assert frontmatter is not None
        assert frontmatter.themes == []
        assert frontmatter.proposed_chunks == []

    def test_parse_frontmatter_with_themes(self, temp_project):
        """Log with themes parses correctly."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes:
  - id: code-refs
    name: Code Reference Friction
  - id: templates
    name: Template System Friction
proposed_chunks: []
---

# Friction Log
""")
        friction = Friction(temp_project)
        frontmatter = friction.parse_frontmatter()

        assert frontmatter is not None
        assert len(frontmatter.themes) == 2
        assert frontmatter.themes[0].id == "code-refs"
        assert frontmatter.themes[1].name == "Template System Friction"

    def test_parse_frontmatter_missing_file(self, temp_project):
        """Returns None for missing file."""
        friction = Friction(temp_project)
        frontmatter = friction.parse_frontmatter()

        assert frontmatter is None

    def test_parse_frontmatter_no_frontmatter(self, temp_project):
        """Returns None if file has no frontmatter."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("# Friction Log\nNo frontmatter here.")

        friction = Friction(temp_project)
        frontmatter = friction.parse_frontmatter()

        assert frontmatter is None


class TestFrictionParseEntries:
    """Tests for Friction.parse_entries method."""

    def test_parse_entries_extracts_fields(self, temp_project):
        """Entry parsing extracts id, date, theme, title, and content."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries

### F001: 2026-01-12 [code-refs] Symbolic references become ambiguous

When multiple CLI commands have functions named `create`, the symbolic
reference `src/ve.py#create` becomes ambiguous.

**Impact**: High
**Frequency**: Recurring
""")
        friction = Friction(temp_project)
        entries = friction.parse_entries()

        assert len(entries) == 1
        assert entries[0].id == "F001"
        assert entries[0].date == "2026-01-12"
        assert entries[0].theme_id == "code-refs"
        assert entries[0].title == "Symbolic references become ambiguous"
        assert "ambiguous" in entries[0].content
        assert "**Impact**: High" in entries[0].content

    def test_parse_entries_multiple(self, temp_project):
        """Multiple entries are all parsed."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries

### F001: 2026-01-12 [code-refs] First friction

First content.

### F002: 2026-01-10 [templates] Second friction

Second content.

### F003: 2026-01-08 [code-refs] Third friction

Third content.
""")
        friction = Friction(temp_project)
        entries = friction.parse_entries()

        assert len(entries) == 3
        assert entries[0].id == "F001"
        assert entries[1].id == "F002"
        assert entries[2].id == "F003"

    def test_parse_entries_empty_log(self, temp_project):
        """Empty log returns empty list."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries

<!-- No entries yet -->
""")
        friction = Friction(temp_project)
        entries = friction.parse_entries()

        assert entries == []

    def test_parse_entries_missing_file(self, temp_project):
        """Missing file returns empty list."""
        friction = Friction(temp_project)
        entries = friction.parse_entries()

        assert entries == []


class TestFrictionGetNextEntryId:
    """Tests for Friction.get_next_entry_id method."""

    def test_get_next_entry_id_empty(self, temp_project):
        """Returns F001 for empty log."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries
""")
        friction = Friction(temp_project)
        next_id = friction.get_next_entry_id()

        assert next_id == "F001"

    def test_get_next_entry_id_sequential(self, temp_project):
        """Returns F004 when F001-F003 exist."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries

### F001: 2026-01-01 [test] First
Content.

### F002: 2026-01-02 [test] Second
Content.

### F003: 2026-01-03 [test] Third
Content.
""")
        friction = Friction(temp_project)
        next_id = friction.get_next_entry_id()

        assert next_id == "F004"

    def test_get_next_entry_id_handles_gaps(self, temp_project):
        """Handles non-sequential IDs correctly (uses max + 1)."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries

### F001: 2026-01-01 [test] First
Content.

### F005: 2026-01-05 [test] Fifth
Content.
""")
        friction = Friction(temp_project)
        next_id = friction.get_next_entry_id()

        assert next_id == "F006"


class TestFrictionGetEntryStatus:
    """Tests for Friction.get_entry_status method."""

    def test_get_entry_status_open(self, temp_project):
        """Entry not in proposed_chunks is OPEN."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log
""")
        friction = Friction(temp_project)
        status = friction.get_entry_status("F001")

        assert status == FrictionStatus.OPEN

    def test_get_entry_status_addressed(self, temp_project):
        """Entry in proposed_chunks with chunk_directory is ADDRESSED."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks:
  - prompt: Fix the issue
    chunk_directory: symbolic_code_refs
    addresses:
      - F001
      - F003
---

# Friction Log
""")
        friction = Friction(temp_project)
        status = friction.get_entry_status("F001")

        assert status == FrictionStatus.ADDRESSED

    def test_get_entry_status_open_when_chunk_not_set(self, temp_project):
        """Entry in proposed_chunks without chunk_directory is still OPEN."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks:
  - prompt: Fix the issue
    chunk_directory: null
    addresses:
      - F001
---

# Friction Log
""")
        friction = Friction(temp_project)
        status = friction.get_entry_status("F001")

        # Entry is in addresses but chunk_directory is null, so still OPEN
        assert status == FrictionStatus.OPEN


class TestFrictionListEntries:
    """Tests for Friction.list_entries method."""

    def test_list_entries_all(self, temp_project):
        """Returns all entries without filters."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries

### F001: 2026-01-01 [code-refs] First
Content.

### F002: 2026-01-02 [templates] Second
Content.
""")
        friction = Friction(temp_project)
        entries = friction.list_entries()

        assert len(entries) == 2
        assert entries[0][0].id == "F001"
        assert entries[1][0].id == "F002"

    def test_list_entries_filter_status(self, temp_project):
        """Filters by status correctly."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks:
  - prompt: Fix F001
    chunk_directory: fix_chunk
    addresses:
      - F001
---

# Friction Log

## Entries

### F001: 2026-01-01 [code-refs] Addressed entry
Content.

### F002: 2026-01-02 [templates] Open entry
Content.
""")
        friction = Friction(temp_project)

        # Only OPEN entries
        open_entries = friction.list_entries(status_filter=FrictionStatus.OPEN)
        assert len(open_entries) == 1
        assert open_entries[0][0].id == "F002"

        # Only ADDRESSED entries
        addressed_entries = friction.list_entries(status_filter=FrictionStatus.ADDRESSED)
        assert len(addressed_entries) == 1
        assert addressed_entries[0][0].id == "F001"

    def test_list_entries_filter_tags(self, temp_project):
        """Filters by theme tag correctly."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries

### F001: 2026-01-01 [code-refs] First
Content.

### F002: 2026-01-02 [templates] Second
Content.

### F003: 2026-01-03 [code-refs] Third
Content.
""")
        friction = Friction(temp_project)
        entries = friction.list_entries(theme_filter="code-refs")

        assert len(entries) == 2
        assert entries[0][0].id == "F001"
        assert entries[1][0].id == "F003"

    def test_list_entries_empty(self, temp_project):
        """Returns empty list for empty log."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries
""")
        friction = Friction(temp_project)
        entries = friction.list_entries()

        assert entries == []


class TestFrictionAppendEntry:
    """Tests for Friction.append_entry method."""

    def test_append_entry_creates_entry(self, temp_project):
        """Appending entry creates it with correct format."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes:
  - id: test-theme
    name: Test Theme
proposed_chunks: []
---

# Friction Log

## Entries
""")
        friction = Friction(temp_project)
        entry_id = friction.append_entry(
            title="Test friction",
            description="This is a test friction description.",
            impact="high",
            theme_id="test-theme",
            entry_date="2026-01-15",
        )

        assert entry_id == "F001"

        # Verify entry was written
        entries = friction.parse_entries()
        assert len(entries) == 1
        assert entries[0].id == "F001"
        assert entries[0].title == "Test friction"
        assert entries[0].theme_id == "test-theme"
        assert "test friction description" in entries[0].content.lower()
        assert "**Impact**: High" in entries[0].content

    def test_append_entry_increments_id(self, temp_project):
        """Appending entries increments the ID sequentially."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes:
  - id: test
    name: Test
proposed_chunks: []
---

# Friction Log

## Entries

### F001: 2026-01-01 [test] First
Content.
""")
        friction = Friction(temp_project)
        entry_id = friction.append_entry(
            title="Second entry",
            description="Description.",
            impact="low",
            theme_id="test",
            entry_date="2026-01-15",
        )

        assert entry_id == "F002"

    def test_append_entry_new_theme(self, temp_project):
        """Appending entry with new theme adds theme to frontmatter."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries
""")
        friction = Friction(temp_project)
        entry_id = friction.append_entry(
            title="New theme entry",
            description="Description.",
            impact="medium",
            theme_id="new-theme",
            theme_name="New Theme Friction",
            entry_date="2026-01-15",
        )

        assert entry_id == "F001"

        # Verify theme was added
        frontmatter = friction.parse_frontmatter()
        assert len(frontmatter.themes) == 1
        assert frontmatter.themes[0].id == "new-theme"
        assert frontmatter.themes[0].name == "New Theme Friction"

    def test_append_entry_existing_theme(self, temp_project):
        """Appending entry with existing theme doesn't change frontmatter."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes:
  - id: existing
    name: Existing Theme
proposed_chunks: []
---

# Friction Log

## Entries
""")
        friction = Friction(temp_project)
        friction.append_entry(
            title="Entry",
            description="Description.",
            impact="low",
            theme_id="existing",
            entry_date="2026-01-15",
        )

        # Verify theme count unchanged
        frontmatter = friction.parse_frontmatter()
        assert len(frontmatter.themes) == 1

    def test_append_entry_new_theme_no_name_raises(self, temp_project):
        """Appending entry with new theme but no name raises ValueError."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries
""")
        friction = Friction(temp_project)

        with pytest.raises(ValueError) as exc_info:
            friction.append_entry(
                title="Entry",
                description="Description.",
                impact="low",
                theme_id="new-theme",
                # No theme_name provided
                entry_date="2026-01-15",
            )

        assert "new" in str(exc_info.value).lower()
        assert "theme_name" in str(exc_info.value)

    def test_append_entry_missing_file_raises(self, temp_project):
        """Appending to missing file raises ValueError."""
        friction = Friction(temp_project)

        with pytest.raises(ValueError) as exc_info:
            friction.append_entry(
                title="Entry",
                description="Description.",
                impact="low",
                theme_id="test",
                theme_name="Test",
            )

        assert "does not exist" in str(exc_info.value)


class TestFrictionAnalyze:
    """Tests for Friction.analyze_by_theme method."""

    def test_analyze_groups_by_theme(self, temp_project):
        """Entries are grouped correctly by theme."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries

### F001: 2026-01-01 [code-refs] First code ref
Content.

### F002: 2026-01-02 [templates] Template issue
Content.

### F003: 2026-01-03 [code-refs] Second code ref
Content.

### F004: 2026-01-04 [code-refs] Third code ref
Content.
""")
        friction = Friction(temp_project)
        analysis = friction.analyze_by_theme()

        assert "code-refs" in analysis
        assert "templates" in analysis
        assert len(analysis["code-refs"]) == 3
        assert len(analysis["templates"]) == 1

    def test_analyze_empty_log(self, temp_project):
        """Empty log returns empty dict."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries
""")
        friction = Friction(temp_project)
        analysis = friction.analyze_by_theme()

        assert analysis == {}

    def test_analyze_with_theme_filter(self, temp_project):
        """Theme filter limits analysis to specific theme."""
        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        friction_path.parent.mkdir(parents=True, exist_ok=True)
        friction_path.write_text("""---
themes: []
proposed_chunks: []
---

# Friction Log

## Entries

### F001: 2026-01-01 [code-refs] First
Content.

### F002: 2026-01-02 [templates] Second
Content.
""")
        friction = Friction(temp_project)
        analysis = friction.analyze_by_theme(theme_filter="code-refs")

        assert "code-refs" in analysis
        assert "templates" not in analysis
        assert len(analysis["code-refs"]) == 1
