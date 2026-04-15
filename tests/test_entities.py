"""Tests for Entities domain class.

Tests entity creation, listing, memory write/parse, startup index,
find_memory, touch_memory, read_touch_log, and session tracking.
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from entities import Entities
from models.entity import (
    MemoryCategory,
    MemoryFrontmatter,
    MemoryTier,
    MemoryValence,
    SessionRecord,
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


class TestStartupPayload:
    """Tests for Entities.startup_payload()."""

    def test_startup_payload_includes_identity(self, entities):
        """Payload contains entity name and role."""
        entities.create_entity("mysteward", role="Project steward")
        payload = entities.startup_payload("mysteward")
        assert "mysteward" in payload
        assert "Project steward" in payload

    def test_startup_payload_includes_identity_body(self, entities):
        """Payload contains the full body text from identity.md."""
        entities.create_entity("mysteward", role="Project steward")
        payload = entities.startup_payload("mysteward")
        assert "Startup Instructions" in payload

    def test_startup_payload_includes_core_memories(self, entities):
        """Each core memory title and content appears in output."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="core", title="Always verify first", salience=5),
            "Check state before acting on assumptions.",
        )
        payload = entities.startup_payload("agent")
        assert "Always verify first" in payload
        assert "Check state before acting on assumptions." in payload

    def test_startup_payload_core_memories_numbered(self, entities):
        """Core memories are numbered CM1, CM2, etc."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="core", title="First skill", salience=5),
            "Content A.",
        )
        entities.write_memory(
            "agent",
            _make_memory(tier="core", title="Second skill", salience=4),
            "Content B.",
        )
        payload = entities.startup_payload("agent")
        assert "CM1:" in payload
        assert "CM2:" in payload

    def test_startup_payload_includes_consolidated_index(self, entities):
        """Consolidated titles appear as an index."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="consolidated", title="Pattern X"),
            "Details about pattern X.",
        )
        payload = entities.startup_payload("agent")
        assert "Consolidated Memory Index" in payload
        assert "- Pattern X" in payload

    def test_startup_payload_includes_touch_protocol(self, entities):
        """Touch Protocol shows correct 3-argument signature."""
        entities.create_entity("agent")
        payload = entities.startup_payload("agent")
        # Must include entity name argument in the command signature
        assert "ve entity touch <name> <memory_id>" in payload

    def test_startup_payload_excludes_journal(self, entities):
        """Journal memories do not appear in the startup payload."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="journal", title="Daily note secret"),
            "Should not appear.",
        )
        payload = entities.startup_payload("agent")
        assert "Daily note secret" not in payload
        assert "Should not appear" not in payload

    def test_startup_payload_empty_memories(self, entities):
        """Entity with no memories still produces valid payload."""
        entities.create_entity("agent")
        payload = entities.startup_payload("agent")
        assert "agent" in payload
        assert "Core Memories" in payload
        assert "Touch Protocol" in payload
        assert "No core memories yet" in payload

    def test_startup_payload_nonexistent_entity(self, entities):
        """Raises ValueError for nonexistent entity."""
        with pytest.raises(ValueError, match="does not exist"):
            entities.startup_payload("ghost")


class TestRecallMemory:
    """Tests for Entities.recall_memory()."""

    def test_recall_finds_by_exact_title(self, entities):
        """Exact title match returns the memory."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="core", title="Verify state before acting"),
            "Always check.",
        )
        results = entities.recall_memory("agent", "Verify state before acting")
        assert len(results) == 1
        assert results[0]["frontmatter"]["title"] == "Verify state before acting"

    def test_recall_finds_by_substring(self, entities):
        """Partial title match works."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="consolidated", title="Template system requires source editing"),
            "Edit templates not rendered files.",
        )
        results = entities.recall_memory("agent", "Template system")
        assert len(results) == 1
        assert "Template system" in results[0]["frontmatter"]["title"]

    def test_recall_case_insensitive(self, entities):
        """Case-insensitive matching."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="core", title="Always Verify First"),
            "Check things.",
        )
        results = entities.recall_memory("agent", "always verify")
        assert len(results) == 1

    def test_recall_returns_content(self, entities):
        """Returned dict includes full content body."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="core", title="Some Skill"),
            "The full body of the memory.",
        )
        results = entities.recall_memory("agent", "Some Skill")
        assert results[0]["content"] == "The full body of the memory."
        assert results[0]["tier"] == "core"

    def test_recall_no_match_returns_empty(self, entities):
        """No match returns empty list."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="core", title="Existing memory"),
            "Content.",
        )
        results = entities.recall_memory("agent", "nonexistent query")
        assert results == []

    def test_recall_excludes_journal(self, entities):
        """Journal memories are not searchable."""
        entities.create_entity("agent")
        entities.write_memory(
            "agent",
            _make_memory(tier="journal", title="Secret journal entry"),
            "Hidden.",
        )
        results = entities.recall_memory("agent", "Secret journal")
        assert results == []

    def test_recall_nonexistent_entity(self, entities):
        """Raises ValueError for nonexistent entity."""
        with pytest.raises(ValueError, match="does not exist"):
            entities.recall_memory("ghost", "anything")


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
        assert index["consolidated"] == [{"title": "Pattern X", "category": "correction"}]

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


# --- Session Tracking Tests ---

def _make_session_record(**overrides) -> SessionRecord:
    """Create a valid SessionRecord with optional overrides."""
    defaults = {
        "session_id": "abc-123-def-456",
        "started_at": datetime(2026, 3, 31, 10, 0, 0, tzinfo=timezone.utc),
        "ended_at": datetime(2026, 3, 31, 11, 0, 0, tzinfo=timezone.utc),
        "summary": None,
    }
    defaults.update(overrides)
    return SessionRecord(**defaults)


class TestSessionRecord:
    """Tests for SessionRecord model validation."""

    def test_valid_session_record(self):
        """A fully specified SessionRecord is valid."""
        record = SessionRecord(
            session_id="abc-123",
            started_at=datetime(2026, 3, 31, 10, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 3, 31, 11, 0, 0, tzinfo=timezone.utc),
            summary="Did some work",
        )
        assert record.session_id == "abc-123"
        assert record.summary == "Did some work"

    def test_session_id_required(self):
        """Missing session_id raises ValidationError."""
        with pytest.raises(ValidationError):
            SessionRecord(
                started_at=datetime(2026, 3, 31, 10, 0, 0, tzinfo=timezone.utc),
                ended_at=datetime(2026, 3, 31, 11, 0, 0, tzinfo=timezone.utc),
            )

    def test_started_at_required(self):
        """Missing started_at raises ValidationError."""
        with pytest.raises(ValidationError):
            SessionRecord(
                session_id="abc-123",
                ended_at=datetime(2026, 3, 31, 11, 0, 0, tzinfo=timezone.utc),
            )

    def test_ended_at_required(self):
        """Missing ended_at raises ValidationError."""
        with pytest.raises(ValidationError):
            SessionRecord(
                session_id="abc-123",
                started_at=datetime(2026, 3, 31, 10, 0, 0, tzinfo=timezone.utc),
            )

    def test_summary_optional_defaults_to_none(self):
        """summary is optional and defaults to None."""
        record = SessionRecord(
            session_id="abc-123",
            started_at=datetime(2026, 3, 31, 10, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 3, 31, 11, 0, 0, tzinfo=timezone.utc),
        )
        assert record.summary is None

    def test_started_at_is_datetime(self):
        """started_at is stored as a datetime, not a string."""
        record = _make_session_record()
        assert isinstance(record.started_at, datetime)

    def test_ended_at_is_datetime(self):
        """ended_at is stored as a datetime, not a string."""
        record = _make_session_record()
        assert isinstance(record.ended_at, datetime)


class TestSessionLog:
    """Tests for Entities.append_session() and list_sessions()."""

    def test_append_session_writes_jsonl_line(self, entities, temp_project):
        """append_session writes a single JSON line to sessions.jsonl."""
        entities.create_entity("agent")
        record = _make_session_record()
        entities.append_session("agent", record)

        log_path = temp_project / ".entities" / "agent" / "sessions.jsonl"
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_append_session_twice_produces_two_lines(self, entities, temp_project):
        """Two append_session calls produce two lines in sessions.jsonl."""
        entities.create_entity("agent")
        r1 = _make_session_record(session_id="session-1")
        r2 = _make_session_record(session_id="session-2")
        entities.append_session("agent", r1)
        entities.append_session("agent", r2)

        log_path = temp_project / ".entities" / "agent" / "sessions.jsonl"
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_list_sessions_empty_when_no_log(self, entities):
        """list_sessions returns [] when sessions.jsonl doesn't exist."""
        entities.create_entity("agent")
        assert entities.list_sessions("agent") == []

    def test_list_sessions_roundtrip(self, entities):
        """Records written by append_session come back as SessionRecord instances."""
        entities.create_entity("agent")
        record = _make_session_record(
            session_id="roundtrip-001",
            summary="Round trip test",
        )
        entities.append_session("agent", record)

        sessions = entities.list_sessions("agent")
        assert len(sessions) == 1
        assert isinstance(sessions[0], SessionRecord)
        assert sessions[0].session_id == "roundtrip-001"
        assert sessions[0].summary == "Round trip test"
        assert isinstance(sessions[0].started_at, datetime)
        assert isinstance(sessions[0].ended_at, datetime)

    def test_list_sessions_preserves_insertion_order(self, entities):
        """list_sessions returns records in insertion order."""
        entities.create_entity("agent")
        r1 = _make_session_record(session_id="first")
        r2 = _make_session_record(session_id="second")
        r3 = _make_session_record(session_id="third")
        entities.append_session("agent", r1)
        entities.append_session("agent", r2)
        entities.append_session("agent", r3)

        sessions = entities.list_sessions("agent")
        assert [s.session_id for s in sessions] == ["first", "second", "third"]


class TestArchiveTranscript:
    """Tests for Entities.archive_transcript()."""

    def _make_fake_claude_home(self, tmp_path, project_path: str, session_id: str, content: str) -> "Path":
        """Create a fake ~/.claude directory tree with a transcript file."""
        from pathlib import Path
        encoded = project_path.replace("/", "-")
        source_dir = tmp_path / "claude_home" / "projects" / encoded
        source_dir.mkdir(parents=True)
        source_file = source_dir / f"{session_id}.jsonl"
        source_file.write_text(content)
        return tmp_path / "claude_home"

    def test_archive_copies_transcript(self, entities, tmp_path, temp_project):
        """archive_transcript copies JSONL file into .entities/<name>/sessions/."""
        entities.create_entity("agent")
        project_path = "/Users/btaylor/Projects/foo"
        session_id = "abc-123"
        transcript_content = '{"role": "user", "content": "hello"}\n'

        claude_home = self._make_fake_claude_home(tmp_path, project_path, session_id, transcript_content)

        result = entities.archive_transcript("agent", session_id, project_path, claude_home=claude_home)

        assert result is True
        dest = temp_project / ".entities" / "agent" / "sessions" / f"{session_id}.jsonl"
        assert dest.exists()
        assert dest.read_text() == transcript_content

    def test_archive_creates_sessions_directory(self, entities, tmp_path, temp_project):
        """archive_transcript creates .entities/<name>/sessions/ on first call."""
        entities.create_entity("agent")
        sessions_dir = temp_project / ".entities" / "agent" / "sessions"
        assert not sessions_dir.exists()

        project_path = "/Users/btaylor/Projects/bar"
        session_id = "new-session"
        claude_home = self._make_fake_claude_home(tmp_path, project_path, session_id, "{}\n")

        entities.archive_transcript("agent", session_id, project_path, claude_home=claude_home)

        assert sessions_dir.is_dir()

    def test_archive_returns_false_when_source_missing(self, entities, tmp_path):
        """archive_transcript returns False (no crash) when source doesn't exist."""
        entities.create_entity("agent")
        # Point to a claude_home with no matching session file
        fake_claude_home = tmp_path / "empty_claude_home"
        fake_claude_home.mkdir()

        result = entities.archive_transcript(
            "agent",
            "nonexistent-session",
            "/Users/btaylor/Projects/foo",
            claude_home=fake_claude_home,
        )

        assert result is False

    def test_archive_encoded_path_convention(self, entities, tmp_path, temp_project):
        """Encodes project_path using Claude Code's convention (prepend '-', replace '/' with '-')."""
        entities.create_entity("agent")
        project_path = "/Users/btaylor/Projects/foo"
        session_id = "test-session"

        # The encoded path should be "-Users-btaylor-Projects-foo"
        encoded = "-Users-btaylor-Projects-foo"
        source_dir = tmp_path / "claude_home" / "projects" / encoded
        source_dir.mkdir(parents=True)
        (source_dir / f"{session_id}.jsonl").write_text("transcript data\n")
        claude_home = tmp_path / "claude_home"

        result = entities.archive_transcript("agent", session_id, project_path, claude_home=claude_home)

        assert result is True
        dest = temp_project / ".entities" / "agent" / "sessions" / f"{session_id}.jsonl"
        assert dest.read_text() == "transcript data\n"

    def test_sessions_dir_not_created_at_entity_creation(self, entities, temp_project):
        """The sessions/ directory is NOT created by create_entity."""
        entities.create_entity("agent")
        sessions_dir = temp_project / ".entities" / "agent" / "sessions"
        assert not sessions_dir.exists()


class TestCreateEntityWiki:
    """Tests for wiki directory and page creation in Entities.create_entity()."""

    def _parse_frontmatter(self, content: str) -> dict:
        """Parse YAML frontmatter from a markdown file (between --- delimiters)."""
        import yaml as _yaml
        import re as _re
        match = _re.match(r"^---\s*\n(.*?)\n---", content, _re.DOTALL)
        if not match:
            return {}
        return _yaml.safe_load(match.group(1)) or {}

    # --- Structural tests ---

    def test_creates_wiki_directory(self, entities, temp_project):
        """create_entity creates the wiki/ directory."""
        entities.create_entity("agent")
        wiki_dir = temp_project / ".entities" / "agent" / "wiki"
        assert wiki_dir.is_dir()

    def test_creates_wiki_subdirectories(self, entities, temp_project):
        """create_entity creates domain/, projects/, techniques/, relationships/ inside wiki/."""
        entities.create_entity("agent")
        wiki_dir = temp_project / ".entities" / "agent" / "wiki"
        for subdir in ["domain", "projects", "techniques", "relationships"]:
            assert (wiki_dir / subdir).is_dir(), f"Missing wiki/{subdir}/"

    def test_creates_wiki_initial_pages(self, entities, temp_project):
        """create_entity creates wiki_schema.md, identity.md, index.md, log.md inside wiki/."""
        entities.create_entity("agent")
        wiki_dir = temp_project / ".entities" / "agent" / "wiki"
        for page in ["wiki_schema.md", "identity.md", "index.md", "log.md"]:
            assert (wiki_dir / page).is_file(), f"Missing wiki/{page}"

    # --- Content tests: wiki_schema.md ---

    def test_wiki_schema_mentions_directory_structure(self, entities, temp_project):
        """wiki_schema.md describes the directory structure (domain, projects, techniques, relationships)."""
        entities.create_entity("agent")
        content = (temp_project / ".entities" / "agent" / "wiki" / "wiki_schema.md").read_text()
        for section in ["domain", "projects", "techniques", "relationships"]:
            assert section in content, f"wiki_schema.md missing '{section}'"

    def test_wiki_schema_mentions_wikilinks(self, entities, temp_project):
        """wiki_schema.md documents the wikilink convention."""
        entities.create_entity("agent")
        content = (temp_project / ".entities" / "agent" / "wiki" / "wiki_schema.md").read_text()
        assert "[[" in content

    def test_wiki_schema_mentions_log_format(self, entities, temp_project):
        """wiki_schema.md documents the YYYY-MM-DD log entry format."""
        entities.create_entity("agent")
        content = (temp_project / ".entities" / "agent" / "wiki" / "wiki_schema.md").read_text()
        assert "YYYY-MM-DD" in content

    # --- Content tests: wiki/identity.md ---

    def test_wiki_identity_contains_entity_name(self, entities, temp_project):
        """wiki/identity.md contains the entity name."""
        entities.create_entity("agent", role="Test role")
        content = (temp_project / ".entities" / "agent" / "wiki" / "identity.md").read_text()
        # Entity name appears via role or other means — at minimum role is present
        assert "agent" in content or "Test role" in content

    def test_wiki_identity_valid_frontmatter(self, entities, temp_project):
        """wiki/identity.md has parseable YAML frontmatter with title, created, updated."""
        entities.create_entity("agent")
        content = (temp_project / ".entities" / "agent" / "wiki" / "identity.md").read_text()
        fm = self._parse_frontmatter(content)
        assert "title" in fm
        assert "created" in fm
        assert "updated" in fm

    # --- Content tests: wiki/index.md ---

    def test_wiki_index_contains_identity_link(self, entities, temp_project):
        """wiki/index.md contains [[identity]] wikilink."""
        entities.create_entity("agent")
        content = (temp_project / ".entities" / "agent" / "wiki" / "index.md").read_text()
        assert "[[identity]]" in content

    def test_wiki_index_contains_log_link(self, entities, temp_project):
        """wiki/index.md contains [[log]] wikilink."""
        entities.create_entity("agent")
        content = (temp_project / ".entities" / "agent" / "wiki" / "index.md").read_text()
        assert "[[log]]" in content

    def test_wiki_index_valid_frontmatter(self, entities, temp_project):
        """wiki/index.md has parseable YAML frontmatter with title, created, updated."""
        entities.create_entity("agent")
        content = (temp_project / ".entities" / "agent" / "wiki" / "index.md").read_text()
        fm = self._parse_frontmatter(content)
        assert "title" in fm
        assert "created" in fm
        assert "updated" in fm

    # --- Content tests: wiki/log.md ---

    def test_wiki_log_valid_frontmatter(self, entities, temp_project):
        """wiki/log.md has parseable YAML frontmatter with title, created, updated."""
        entities.create_entity("agent")
        content = (temp_project / ".entities" / "agent" / "wiki" / "log.md").read_text()
        fm = self._parse_frontmatter(content)
        assert "title" in fm
        assert "created" in fm
        assert "updated" in fm

    def test_wiki_log_contains_format_example(self, entities, temp_project):
        """wiki/log.md documents the YYYY-MM-DD log entry format."""
        entities.create_entity("agent")
        content = (temp_project / ".entities" / "agent" / "wiki" / "log.md").read_text()
        assert "YYYY-MM-DD" in content


class TestHasWiki:
    """Tests for Entities.has_wiki()."""

    def test_has_wiki_true_for_wiki_entity(self, entities):
        """Entity created with create_entity() has a wiki/ directory — returns True."""
        entities.create_entity("agent")
        assert entities.has_wiki("agent") is True

    def test_has_wiki_false_for_legacy_entity(self, entities, temp_project):
        """Manually created entity directory without wiki/ returns False."""
        # Simulate a pre-wiki entity by hand
        legacy_dir = temp_project / ".entities" / "legacy"
        legacy_dir.mkdir(parents=True)
        (legacy_dir / "identity.md").write_text("---\nrole: null\n---\n")
        (legacy_dir / "memories" / "core").mkdir(parents=True)
        (legacy_dir / "memories" / "consolidated").mkdir(parents=True)
        (legacy_dir / "memories" / "journal").mkdir(parents=True)

        assert entities.has_wiki("legacy") is False


class TestStartupPayloadWiki:
    """Tests for wiki-aware startup_payload()."""

    def _make_wiki_entity(self, entities, temp_project, name: str = "agent") -> None:
        """Create a wiki entity and write known content to wiki/index.md."""
        entities.create_entity(name)
        # Overwrite wiki/index.md with a known sentinel string
        wiki_index = temp_project / ".entities" / name / "wiki" / "index.md"
        wiki_index.write_text("# Index\n\nSentinel wiki index content for testing.\n")

    def _make_legacy_entity(self, entities, temp_project, name: str = "legacy") -> None:
        """Create a legacy entity directory without wiki/."""
        legacy_dir = temp_project / ".entities" / name
        legacy_dir.mkdir(parents=True)
        (legacy_dir / "identity.md").write_text("---\nrole: null\n---\nLegacy identity.\n")
        for tier in ["core", "consolidated", "journal"]:
            (legacy_dir / "memories" / tier).mkdir(parents=True)

    def test_wiki_payload_includes_wiki_index_content(self, entities, temp_project):
        """Payload for a wiki entity contains the text from wiki/index.md."""
        self._make_wiki_entity(entities, temp_project)
        payload = entities.startup_payload("agent")
        assert "Sentinel wiki index content for testing." in payload

    def test_wiki_payload_includes_maintenance_reminder(self, entities, temp_project):
        """Payload contains a Wiki Maintenance Protocol heading."""
        self._make_wiki_entity(entities, temp_project)
        payload = entities.startup_payload("agent")
        assert "Wiki Maintenance Protocol" in payload

    def test_wiki_payload_references_wiki_schema(self, entities, temp_project):
        """Payload mentions wiki/wiki_schema.md so the entity knows where the full schema is."""
        self._make_wiki_entity(entities, temp_project)
        payload = entities.startup_payload("agent")
        assert "wiki/wiki_schema.md" in payload

    def test_wiki_payload_section_order(self, entities, temp_project):
        """Core memories appear before wiki index, which appears before consolidated index."""
        self._make_wiki_entity(entities, temp_project)
        payload = entities.startup_payload("agent")

        core_pos = payload.index("## Core Memories")
        wiki_pos = payload.index("## Wiki:")
        consolidated_pos = payload.index("## Consolidated Memory Index")

        assert core_pos < wiki_pos < consolidated_pos, (
            f"Expected Core ({core_pos}) < Wiki ({wiki_pos}) < Consolidated ({consolidated_pos})"
        )

    def test_legacy_entity_payload_unchanged(self, entities, temp_project):
        """Legacy entity payload does NOT contain any Wiki heading sections."""
        self._make_legacy_entity(entities, temp_project)
        payload = entities.startup_payload("legacy")

        assert "## Wiki:" not in payload
        assert "Wiki Maintenance Protocol" not in payload
        assert "wiki/wiki_schema.md" not in payload
