"""Tests for entity domain models.

Validates Pydantic models for memory frontmatter and entity identity.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from models.entity import (
    EntityIdentity,
    MemoryCategory,
    MemoryFrontmatter,
    MemoryTier,
    MemoryValence,
)


class TestMemoryFrontmatter:
    """Tests for MemoryFrontmatter schema validation."""

    def _make_valid(self, **overrides):
        """Create a valid MemoryFrontmatter dict with optional overrides."""
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
        return defaults

    def test_valid_memory(self):
        """Accepts valid memory frontmatter."""
        fm = MemoryFrontmatter(**self._make_valid())
        assert fm.title == "Test memory"
        assert fm.category == MemoryCategory.CORRECTION
        assert fm.valence == MemoryValence.NEGATIVE
        assert fm.salience == 3
        assert fm.tier == MemoryTier.JOURNAL

    def test_rejects_salience_below_1(self):
        """Salience must be at least 1."""
        with pytest.raises(ValidationError, match="salience"):
            MemoryFrontmatter(**self._make_valid(salience=0))

    def test_rejects_salience_above_5(self):
        """Salience must be at most 5."""
        with pytest.raises(ValidationError, match="salience"):
            MemoryFrontmatter(**self._make_valid(salience=6))

    def test_rejects_invalid_tier(self):
        """Rejects invalid tier values."""
        with pytest.raises(ValidationError):
            MemoryFrontmatter(**self._make_valid(tier="invalid"))

    def test_rejects_invalid_category(self):
        """Rejects invalid category values."""
        with pytest.raises(ValidationError):
            MemoryFrontmatter(**self._make_valid(category="invalid"))

    def test_rejects_invalid_valence(self):
        """Rejects invalid valence values."""
        with pytest.raises(ValidationError):
            MemoryFrontmatter(**self._make_valid(valence="invalid"))

    def test_rejects_negative_recurrence_count(self):
        """Recurrence count must be >= 0."""
        with pytest.raises(ValidationError, match="recurrence_count"):
            MemoryFrontmatter(**self._make_valid(recurrence_count=-1))

    def test_source_memories_default_empty(self):
        """Source memories defaults to empty list."""
        fm = MemoryFrontmatter(**self._make_valid())
        assert fm.source_memories == []

    def test_source_memories_populated(self):
        """Source memories can be populated for consolidated/core tiers."""
        fm = MemoryFrontmatter(
            **self._make_valid(
                tier="consolidated",
                source_memories=["Memory A", "Memory B"],
            )
        )
        assert fm.source_memories == ["Memory A", "Memory B"]

    def test_all_categories(self):
        """All category values are accepted."""
        for cat in MemoryCategory:
            fm = MemoryFrontmatter(**self._make_valid(category=cat.value))
            assert fm.category == cat

    def test_all_tiers(self):
        """All tier values are accepted."""
        for tier in MemoryTier:
            fm = MemoryFrontmatter(**self._make_valid(tier=tier.value))
            assert fm.tier == tier

    def test_all_valences(self):
        """All valence values are accepted."""
        for val in MemoryValence:
            fm = MemoryFrontmatter(**self._make_valid(valence=val.value))
            assert fm.valence == val

    def test_prototype_tier2_roundtrip(self):
        """Prototype tier-2 core memory data from the investigation parses without loss."""
        prototype_data = {
            "title": "Verify state before acting",
            "content": "Always check the current state of a resource before taking action...",
            "valence": "negative",
            "category": "correction",
            "salience": 5,
            "tier": 2,  # Prototype used integer tiers
            "source_memories": ["Check PR state before acting", "Validate assumptions first"],
            "recurrence_count": 5,
        }

        # Convert prototype format to our schema
        tier_map = {0: "journal", 1: "consolidated", 2: "core"}
        adapted = {
            "title": prototype_data["title"],
            "category": prototype_data["category"],
            "valence": prototype_data["valence"],
            "salience": prototype_data["salience"],
            "tier": tier_map[prototype_data["tier"]],
            "last_reinforced": datetime.now(timezone.utc),
            "recurrence_count": prototype_data["recurrence_count"],
            "source_memories": prototype_data["source_memories"],
        }

        fm = MemoryFrontmatter(**adapted)
        assert fm.title == "Verify state before acting"
        assert fm.category == MemoryCategory.CORRECTION
        assert fm.valence == MemoryValence.NEGATIVE
        assert fm.salience == 5
        assert fm.tier == MemoryTier.CORE
        assert fm.recurrence_count == 5
        assert fm.source_memories == ["Check PR state before acting", "Validate assumptions first"]

    def test_prototype_tier1_roundtrip(self):
        """Prototype tier-1 consolidated memory parses without loss."""
        adapted = {
            "title": "Template system requires source editing",
            "category": "skill",
            "valence": "neutral",
            "salience": 3,
            "tier": "consolidated",
            "last_reinforced": datetime.now(timezone.utc),
            "recurrence_count": 3,
            "source_memories": ["Edit templates not rendered files"],
        }

        fm = MemoryFrontmatter(**adapted)
        assert fm.title == "Template system requires source editing"
        assert fm.tier == MemoryTier.CONSOLIDATED
        assert fm.recurrence_count == 3

    def test_prototype_tier0_roundtrip(self):
        """Prototype tier-0 journal memory parses without loss."""
        adapted = {
            "title": "Operator prefers concise commit messages",
            "category": "domain",
            "valence": "positive",
            "salience": 2,
            "tier": "journal",
            "last_reinforced": datetime.now(timezone.utc),
            "recurrence_count": 0,
        }

        fm = MemoryFrontmatter(**adapted)
        assert fm.title == "Operator prefers concise commit messages"
        assert fm.tier == MemoryTier.JOURNAL
        assert fm.recurrence_count == 0
        assert fm.source_memories == []

    def test_model_dump_roundtrip(self):
        """model_dump -> model_validate round-trips without loss."""
        fm = MemoryFrontmatter(**self._make_valid(
            source_memories=["A", "B"],
            salience=4,
        ))
        dumped = fm.model_dump()
        restored = MemoryFrontmatter.model_validate(dumped)
        assert restored == fm


class TestEntityIdentity:
    """Tests for EntityIdentity schema validation."""

    def test_valid_name(self):
        """Accepts valid entity names."""
        identity = EntityIdentity(
            name="mysteward",
            created=datetime.now(timezone.utc),
        )
        assert identity.name == "mysteward"
        assert identity.role is None

    def test_valid_name_with_underscores(self):
        """Accepts names with underscores."""
        identity = EntityIdentity(
            name="my_steward_01",
            created=datetime.now(timezone.utc),
        )
        assert identity.name == "my_steward_01"

    def test_valid_name_with_role(self):
        """Accepts name with role."""
        identity = EntityIdentity(
            name="steward",
            role="Project steward for code reviews",
            created=datetime.now(timezone.utc),
        )
        assert identity.role == "Project steward for code reviews"

    def test_rejects_name_with_spaces(self):
        """Rejects names containing spaces."""
        with pytest.raises(ValidationError, match="Entity name"):
            EntityIdentity(name="my steward", created=datetime.now(timezone.utc))

    def test_rejects_name_with_uppercase(self):
        """Rejects names with uppercase letters."""
        with pytest.raises(ValidationError, match="Entity name"):
            EntityIdentity(name="MySteward", created=datetime.now(timezone.utc))

    def test_rejects_name_with_special_chars(self):
        """Rejects names with special characters."""
        with pytest.raises(ValidationError, match="Entity name"):
            EntityIdentity(name="my-steward!", created=datetime.now(timezone.utc))

    def test_rejects_name_with_hyphens(self):
        """Rejects names with hyphens (only underscores allowed)."""
        with pytest.raises(ValidationError, match="Entity name"):
            EntityIdentity(name="my-steward", created=datetime.now(timezone.utc))

    def test_rejects_name_starting_with_digit(self):
        """Rejects names starting with a digit."""
        with pytest.raises(ValidationError, match="Entity name"):
            EntityIdentity(name="1steward", created=datetime.now(timezone.utc))

    def test_rejects_empty_name(self):
        """Rejects empty names."""
        with pytest.raises(ValidationError):
            EntityIdentity(name="", created=datetime.now(timezone.utc))
