"""Tests for Entities domain class.

Tests entity creation, listing, memory write/parse, startup index,
find_memory, touch_memory, and read_touch_log.
"""

import json
from datetime import datetime, timezone

import pytest

from entities import Entities
from models.entity import (
    MemoryCategory,
    MemoryFrontmatter,
    MemoryTier,
    MemoryValence,
    TouchEvent,
)


@pytest.fixture
def entities(temp_project):
    """Create an Entities instance with a temp project directory."""
    return Entities(temp_project)


def _make_memory(**overrides) -> MemoryFrontmatter:
    """Create a valid MemoryFrontmatter with optional overrides."""
    defaults = {
        "title": "Test memory",
        "category": "correction",
        "valence": "negative",
        "salience": 3,
        "tier": "journal",
        "last_reinforced": datetime.now(timezone.utc),
        "recurrence_count": 1,
    }
    defaults.update(overrides)
    return MemoryFrontmatter(**defaults)


class TestCreateEntity:
    """Tests for Entities.create_entity()."""

    def test_creates_directory_structure(self, entities, temp_project):
        """create_entity creates the full directory tree."""
        path = entities.create_entity("mysteward")

        assert path == temp_project / ".entities" / "mysteward"
        assert path.is_dir()
        assert (path / "identity.md").is_file()
        assert (path / "memories" / "journal").is_dir()
        assert (path / "memories" / "consolidated").is_dir()
        assert (path / "memories" / "core").is_dir()

    def test_identity_md_contains_name(self, entities):
        """identity.md includes the entity name."""
        entities.create_entity("mysteward", role="Project steward")
        content = (entities.entity_dir("mysteward") / "identity.md").read_text()
        assert "mysteward" in content
        assert "Project steward" in content

    def test_identity_parseable(self, entities):
        """identity.md is parseable as EntityIdentity."""
        entities.create_entity("mysteward", role="Test role")
        identity = entities.parse_identity("mysteward")
        assert identity is not None
        assert identity.name == "mysteward"
        assert identity.role == "Test role"

    def test_raises_on_duplicate(self, entities):
        """Raises ValueError on duplicate entity creation."""
        entities.create_entity("mysteward")
        with pytest.raises(ValueError, match="already exists"):
            entities.create_entity("mysteward")

    def test_raises_on_invalid_name_spaces(self, entities):
        """Raises ValueError for names with spaces."""
        with pytest.raises(ValueError, match="Invalid entity name"):
            entities.create_entity("my steward")

    def test_raises_on_invalid_name_uppercase(self, entities):
        """Raises ValueError for names with uppercase."""
        with pytest.raises(ValueError, match="Invalid entity name"):
            entities.create_entity("MySteward")

    def test_raises_on_invalid_name_special_chars(self, entities):
        """Raises ValueError for names with special characters."""
        with pytest.raises(ValueError, match="Invalid entity name"):
            entities.create_entity("my-steward!")

    def test_raises_on_name_starting_with_digit(self, entities):
        """Raises ValueError for names starting with digit."""
        with pytest.raises(ValueError, match="Invalid entity name"):
            entities.create_entity("1steward")

    def test_create_without_role(self, entities):
        """Entity can be created without a role."""
        entities.create_entity("bare")
        identity = entities.parse_identity("bare")
        assert identity is not None
        assert identity.name == "bare"
        # Role may be None or empty string depending on template
        assert not identity.role or identity.role == ""


class TestListEntities:
    """Tests for Entities.list_entities()."""

    def test_empty_when_no_entities(self, entities):
        """Returns empty list when no entities exist."""
        assert entities.list_entities() == []

    def test_empty_when_no_entities_dir(self, entities):
        """Returns empty list when .entities/ doesn't exist."""
        assert entities.list_entities() == []

    def test_lists_after_creation(self, entities):
        """Returns entity names after creation."""
        entities.create_entity("alpha")
        entities.create_entity("beta")
        names = entities.list_entities()
        assert names == ["alpha", "beta"]

    def test_sorted_alphabetically(self, entities):
        """Returns names sorted alphabetically."""
        entities.create_entity("zebra")
        entities.create_entity("alpha")
        assert entities.list_entities() == ["alpha", "zebra"]


class TestEntityExists:
    """Tests for Entities.entity_exists()."""

    def test_false_when_not_created(self, entities):
        assert not entities.entity_exists("nonexistent")

    def test_true_after_creation(self, entities):
        entities.create_entity("mysteward")
        assert entities.entity_exists("mysteward")


class TestWriteAndParseMemory:
    """Tests for memory write/parse round-trip."""

    def test_write_creates_file_in_tier_dir(self, entities):
        """write_memory creates file in the correct tier directory."""
        entities.create_entity("agent")
        memory = _make_memory(tier="journal")
        path = entities.write_memory("agent", memory, "Some content here.")

        assert path.exists()
        assert "journal" in str(path)
        assert path.suffix == ".md"

    def test_parse_roundtrip(self, entities):
        """write then parse returns matching data."""
        entities.create_entity("agent")
        original = _make_memory(
            title="Round trip test",
            category="skill",
            valence="positive",
            salience=4,
            tier="consolidated",
            recurrence_count=3,
            source_memories=["Source A", "Source B"],
        )
        content = "This is the memory content body."
        path = entities.write_memory("agent", original, content)

        parsed_fm, parsed_content = entities.parse_memory(path)
        assert parsed_fm is not None
        assert parsed_fm.title == "Round trip test"
        assert parsed_fm.category == MemoryCategory.SKILL
        assert parsed_fm.valence == MemoryValence.POSITIVE
        assert parsed_fm.salience == 4
        assert parsed_fm.tier == MemoryTier.CONSOLIDATED
        assert parsed_fm.recurrence_count == 3
        assert parsed_fm.source_memories == ["Source A", "Source B"]
        assert parsed_content == "This is the memory content body."

    def test_write_core_memory(self, entities):
        """Core memories are stored in the core tier directory."""
        entities.create_entity("agent")
        memory = _make_memory(tier="core", salience=5)
        path = entities.write_memory("agent", memory, "Critical skill.")

        assert "core" in str(path)

    def test_prototype_tier2_roundtrip(self, entities):
        """Prototype tier-2 memories from the investigation store without loss."""
        entities.create_entity("agent")

        # Simulate prototype data adapted to our schema
        now = datetime.now(timezone.utc)
        memory = MemoryFrontmatter(
            title="Verify state before acting",
            category="correction",
            valence="negative",
            salience=5,
            tier="core",
            last_reinforced=now,
            recurrence_count=5,
            source_memories=["Check PR state before acting", "Validate assumptions first"],
        )
        content = "Always check the current state of a resource before taking action on assumptions about its state."

        path = entities.write_memory("agent", memory, content)
        parsed_fm, parsed_content = entities.parse_memory(path)

        assert parsed_fm is not None
        assert parsed_fm.title == "Verify state before acting"
        assert parsed_fm.category == MemoryCategory.CORRECTION
        assert parsed_fm.salience == 5
        assert parsed_fm.tier == MemoryTier.CORE
        assert parsed_fm.recurrence_count == 5
        assert parsed_fm.source_memories == ["Check PR state before acting", "Validate assumptions first"]
        assert "Always check the current state" in parsed_content

    def test_prototype_tier1_roundtrip(self, entities):
        """Prototype tier-1 consolidated memories store without loss."""
        entities.create_entity("agent")

        memory = MemoryFrontmatter(
            title="Template system requires source editing",
            category="skill",
            valence="neutral",
            salience=3,
            tier="consolidated",
            last_reinforced=datetime.now(timezone.utc),
            recurrence_count=3,
            source_memories=["Edit templates not rendered files"],
        )
        content = "Always edit Jinja2 source templates, never rendered output files."

        path = entities.write_memory("agent", memory, content)
        parsed_fm, parsed_content = entities.parse_memory(path)

        assert parsed_fm is not None
        assert parsed_fm.title == "Template system requires source editing"
        assert parsed_fm.tier == MemoryTier.CONSOLIDATED

    def test_prototype_tier0_roundtrip(self, entities):
        """Prototype tier-0 journal memories store without loss."""
        entities.create_entity("agent")

        memory = MemoryFrontmatter(
            title="Operator prefers concise commit messages",
            category="domain",
            valence="positive",
            salience=2,
            tier="journal",
            last_reinforced=datetime.now(timezone.utc),
            recurrence_count=0,
        )
        content = "Today the operator asked for shorter commit messages."

        path = entities.write_memory("agent", memory, content)
        parsed_fm, parsed_content = entities.parse_memory(path)

        assert parsed_fm is not None
        assert parsed_fm.tier == MemoryTier.JOURNAL
        assert parsed_fm.recurrence_count == 0
        assert parsed_fm.source_memories == []


class TestUpdateMemoryField:
    """Tests for Entities.update_memory_field()."""

    def test_update_last_reinforced(self, entities):
        """Updates last_reinforced without corrupting other fields."""
        entities.create_entity("agent")
        memory = _make_memory(
            title="Updatable memory",
            salience=3,
            tier="journal",
        )
        path = entities.write_memory("agent", memory, "Original content.")

        new_time = "2025-12-25T12:00:00+00:00"
        entities.update_memory_field(path, "last_reinforced", new_time)

        parsed_fm, parsed_content = entities.parse_memory(path)
        assert parsed_fm is not None
        assert parsed_fm.title == "Updatable memory"
        assert parsed_fm.salience == 3
        assert "Original content" in parsed_content

    def test_update_recurrence_count(self, entities):
        """Updates recurrence_count preserving other fields."""
        entities.create_entity("agent")
        memory = _make_memory(title="Count test", recurrence_count=1)
        path = entities.write_memory("agent", memory, "Content.")

        entities.update_memory_field(path, "recurrence_count", 5)

        parsed_fm, _ = entities.parse_memory(path)
        assert parsed_fm is not None
        assert parsed_fm.recurrence_count == 5
        assert parsed_fm.title == "Count test"


class TestListMemories:
    """Tests for Entities.list_memories()."""

    def test_empty_when_no_memories(self, entities):
        """Returns empty list when entity has no memories."""
        entities.create_entity("agent")
        assert entities.list_memories("agent") == []

    def test_lists_all_tiers(self, entities):
        """Returns memories from all tiers when no filter."""
        entities.create_entity("agent")
        entities.write_memory("agent", _make_memory(tier="journal", title="J1"), "j")
        entities.write_memory("agent", _make_memory(tier="consolidated", title="C1"), "c")
        entities.write_memory("agent", _make_memory(tier="core", title="K1"), "k")

        memories = entities.list_memories("agent")
        titles = {m.title for m in memories}
        assert titles == {"J1", "C1", "K1"}

    def test_filter_by_tier(self, entities):
        """Returns only memories from the specified tier."""
        entities.create_entity("agent")
        entities.write_memory("agent", _make_memory(tier="journal", title="J1"), "j")
        entities.write_memory("agent", _make_memory(tier="core", title="K1"), "k")

        journal_memories = entities.list_memories("agent", tier=MemoryTier.JOURNAL)
        assert len(journal_memories) == 1
        assert journal_memories[0].title == "J1"

        core_memories = entities.list_memories("agent", tier=MemoryTier.CORE)
        assert len(core_memories) == 1
        assert core_memories[0].title == "K1"


class TestMemoryIndex:
    """Tests for Entities.memory_index()."""

    def test_core_memories_full_content(self, entities):
        """Core memories appear in full with frontmatter and content."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="core", title="Core skill", salience=5),
            "Full content of core skill.",
        )

        index = entities.memory_index("agent")
        assert len(index["core"]) == 1
        assert index["core"][0]["frontmatter"]["title"] == "Core skill"
        assert index["core"][0]["content"] == "Full content of core skill."

    def test_consolidated_titles_only(self, entities):
        """Consolidated memories appear as titles only."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="consolidated", title="Pattern X"),
            "Detailed pattern description.",
        )

        index = entities.memory_index("agent")
        assert index["consolidated"] == ["Pattern X"]

    def test_journal_not_in_index(self, entities):
        """Journal memories are not included in the startup index."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="journal", title="Daily note"),
            "Today I learned...",
        )

        index = entities.memory_index("agent")
        assert index["core"] == []
        assert index["consolidated"] == []

    def test_empty_index_for_new_entity(self, entities):
        """New entity has empty index."""
        entities.create_entity("agent")
        index = entities.memory_index("agent")
        assert index == {"core": [], "consolidated": []}


class TestFindMemory:
    """Tests for Entities.find_memory()."""

    def test_finds_core_memory(self, entities):
        """Finds a core memory by filename stem."""
        entities.create_entity("agent")
        memory = _make_memory(tier="core", title="Core skill")
        path = entities.write_memory("agent", memory, "Core content.")

        result = entities.find_memory("agent", path.stem)
        assert result is not None
        assert result == path

    def test_finds_consolidated_memory(self, entities):
        """Finds a consolidated memory by filename stem."""
        entities.create_entity("agent")
        memory = _make_memory(tier="consolidated", title="Consolidated pattern")
        path = entities.write_memory("agent", memory, "Consolidated content.")

        result = entities.find_memory("agent", path.stem)
        assert result is not None
        assert result == path

    def test_finds_journal_memory(self, entities):
        """Finds a journal memory by filename stem."""
        entities.create_entity("agent")
        memory = _make_memory(tier="journal", title="Journal entry")
        path = entities.write_memory("agent", memory, "Journal content.")

        result = entities.find_memory("agent", path.stem)
        assert result is not None
        assert result == path

    def test_returns_none_for_nonexistent(self, entities):
        """Returns None for a nonexistent memory_id."""
        entities.create_entity("agent")
        assert entities.find_memory("agent", "nonexistent_memory") is None

    def test_searches_core_first(self, entities, temp_project):
        """Searches core tier first (optimization for common case)."""
        entities.create_entity("agent")
        # Manually create files with the same stem in core and journal
        core_dir = temp_project / ".entities" / "agent" / "memories" / "core"
        journal_dir = temp_project / ".entities" / "agent" / "memories" / "journal"

        # Create a memory file with the same stem in both tiers
        stem = "duplicate_memory"
        core_path = core_dir / f"{stem}.md"
        journal_path = journal_dir / f"{stem}.md"
        core_path.write_text("---\ntitle: Core version\n---\n")
        journal_path.write_text("---\ntitle: Journal version\n---\n")

        result = entities.find_memory("agent", stem)
        assert result == core_path  # Core should be found first


class TestTouchMemory:
    """Tests for Entities.touch_memory()."""

    def test_updates_last_reinforced(self, entities):
        """Touch updates last_reinforced on the memory file."""
        entities.create_entity("agent")
        memory = _make_memory(tier="core", title="Touchable skill")
        path = entities.write_memory("agent", memory, "Skill content.")

        before_touch = datetime.now(timezone.utc)
        entities.touch_memory("agent", path.stem)

        parsed_fm, _ = entities.parse_memory(path)
        assert parsed_fm is not None
        # last_reinforced should be updated to approximately now
        assert parsed_fm.last_reinforced >= before_touch

    def test_appends_touch_event_to_log(self, entities, temp_project):
        """Touch appends a TouchEvent to touch_log.jsonl."""
        entities.create_entity("agent")
        memory = _make_memory(tier="core", title="Logged skill")
        path = entities.write_memory("agent", memory, "Content.")

        entities.touch_memory("agent", path.stem)

        log_path = temp_project / ".entities" / "agent" / "touch_log.jsonl"
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        event_data = json.loads(lines[0])
        assert event_data["memory_id"] == path.stem
        assert event_data["memory_title"] == "Logged skill"

    def test_creates_touch_log_if_not_exists(self, entities, temp_project):
        """Touch creates touch_log.jsonl if it doesn't exist."""
        entities.create_entity("agent")
        memory = _make_memory(tier="core", title="New log test")
        path = entities.write_memory("agent", memory, "Content.")

        log_path = temp_project / ".entities" / "agent" / "touch_log.jsonl"
        assert not log_path.exists()

        entities.touch_memory("agent", path.stem)
        assert log_path.exists()

    def test_appends_to_existing_touch_log(self, entities, temp_project):
        """Touch appends to an existing touch_log.jsonl."""
        entities.create_entity("agent")
        mem1 = _make_memory(tier="core", title="First skill")
        path1 = entities.write_memory("agent", mem1, "Content 1.")
        mem2 = _make_memory(tier="core", title="Second skill")
        path2 = entities.write_memory("agent", mem2, "Content 2.")

        entities.touch_memory("agent", path1.stem)
        entities.touch_memory("agent", path2.stem)

        log_path = temp_project / ".entities" / "agent" / "touch_log.jsonl"
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_records_reason_when_provided(self, entities, temp_project):
        """Touch records reason in the touch event."""
        entities.create_entity("agent")
        memory = _make_memory(tier="core", title="Reason test")
        path = entities.write_memory("agent", memory, "Content.")

        entities.touch_memory("agent", path.stem, reason="applying lifecycle rule")

        log_path = temp_project / ".entities" / "agent" / "touch_log.jsonl"
        event_data = json.loads(log_path.read_text().strip())
        assert event_data["reason"] == "applying lifecycle rule"

    def test_omits_reason_when_not_provided(self, entities, temp_project):
        """Touch omits reason when not provided."""
        entities.create_entity("agent")
        memory = _make_memory(tier="core", title="No reason test")
        path = entities.write_memory("agent", memory, "Content.")

        entities.touch_memory("agent", path.stem)

        log_path = temp_project / ".entities" / "agent" / "touch_log.jsonl"
        event_data = json.loads(log_path.read_text().strip())
        assert event_data["reason"] is None

    def test_raises_on_missing_entity(self, entities):
        """Raises ValueError when entity doesn't exist."""
        with pytest.raises(ValueError, match="does not exist"):
            entities.touch_memory("nonexistent", "some_memory")

    def test_raises_on_missing_memory(self, entities):
        """Raises ValueError when memory_id is not found."""
        entities.create_entity("agent")
        with pytest.raises(ValueError, match="not found"):
            entities.touch_memory("agent", "nonexistent_memory")

    def test_touch_event_includes_memory_title(self, entities):
        """The returned touch event includes the memory's title."""
        entities.create_entity("agent")
        memory = _make_memory(tier="core", title="Title check skill")
        path = entities.write_memory("agent", memory, "Content.")

        event = entities.touch_memory("agent", path.stem)
        assert event.memory_title == "Title check skill"
        assert event.memory_id == path.stem


class TestReadTouchLog:
    """Tests for Entities.read_touch_log()."""

    def test_reads_multiple_events_in_order(self, entities):
        """Read touch log returns all events in chronological order."""
        entities.create_entity("agent")
        mem1 = _make_memory(tier="core", title="First")
        path1 = entities.write_memory("agent", mem1, "C1.")
        mem2 = _make_memory(tier="core", title="Second")
        path2 = entities.write_memory("agent", mem2, "C2.")
        mem3 = _make_memory(tier="core", title="Third")
        path3 = entities.write_memory("agent", mem3, "C3.")

        entities.touch_memory("agent", path1.stem, reason="r1")
        entities.touch_memory("agent", path2.stem)
        entities.touch_memory("agent", path3.stem, reason="r3")

        events = entities.read_touch_log("agent")
        assert len(events) == 3
        assert events[0].memory_title == "First"
        assert events[0].reason == "r1"
        assert events[1].memory_title == "Second"
        assert events[1].reason is None
        assert events[2].memory_title == "Third"
        assert events[2].reason == "r3"

    def test_empty_when_no_log(self, entities):
        """Returns empty list when no touch log exists."""
        entities.create_entity("agent")
        assert entities.read_touch_log("agent") == []

    def test_returns_touch_event_instances(self, entities):
        """Each returned item is a TouchEvent instance."""
        entities.create_entity("agent")
        memory = _make_memory(tier="core", title="Type check")
        path = entities.write_memory("agent", memory, "Content.")
        entities.touch_memory("agent", path.stem)

        events = entities.read_touch_log("agent")
        assert len(events) == 1
        assert isinstance(events[0], TouchEvent)
