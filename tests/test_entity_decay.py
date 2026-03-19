"""Tests for entity memory decay mechanics.

# Chunk: docs/chunks/entity_memory_decay

Tests the pure decay logic in apply_decay() against the success criteria
from the chunk GOAL.md:
- Tier-0 expiry after N cycles without association
- Tier-1 salience decay and expiry without reinforcement
- Tier-2 demotion when unreinforced and under capacity pressure
- Reinforcement signals (touch + consolidation) prevent decay
- Boundedness over 20+ simulated cycles
- Audit event generation
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from entity_decay import DecayResult, apply_decay
from models.entity import (
    DecayConfig,
    DecayEvent,
    MemoryCategory,
    MemoryFrontmatter,
    MemoryTier,
    MemoryValence,
)


def _make_memory(
    title: str = "Test memory",
    tier: MemoryTier = MemoryTier.JOURNAL,
    salience: int = 3,
    last_reinforced: datetime | None = None,
    recurrence_count: int = 0,
    category: MemoryCategory = MemoryCategory.SKILL,
) -> tuple[MemoryFrontmatter, str, Path]:
    """Create a test memory tuple for use with apply_decay()."""
    if last_reinforced is None:
        last_reinforced = datetime.now(timezone.utc)
    fm = MemoryFrontmatter(
        title=title,
        category=category,
        valence=MemoryValence.NEUTRAL,
        salience=salience,
        tier=tier,
        last_reinforced=last_reinforced,
        recurrence_count=recurrence_count,
    )
    path = Path(f"/fake/memories/{tier.value}/{title.replace(' ', '_').lower()}.md")
    return (fm, f"Content for {title}", path)


NOW = datetime(2026, 3, 19, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Recency-based decay: Tier 0 (journal)
# ---------------------------------------------------------------------------


class TestTier0Decay:
    def test_tier0_expires_after_n_cycles_without_association(self):
        """Journal memories expire after tier0_expiry_cycles days."""
        config = DecayConfig(tier0_expiry_cycles=5)
        old_time = NOW - timedelta(days=6)
        mem = _make_memory("Old journal", tier=MemoryTier.JOURNAL, last_reinforced=old_time)

        result = apply_decay([mem], NOW, config)

        assert len(result.expirations) == 1
        assert result.expirations[0][0].title == "Old journal"
        assert len(result.survivors) == 0

    def test_tier0_survives_when_recently_reinforced(self):
        """Journal memory with recent last_reinforced survives."""
        config = DecayConfig(tier0_expiry_cycles=5)
        recent_time = NOW - timedelta(days=2)
        mem = _make_memory("Recent journal", tier=MemoryTier.JOURNAL, last_reinforced=recent_time)

        result = apply_decay([mem], NOW, config)

        assert len(result.survivors) == 1
        assert len(result.expirations) == 0

    def test_tier0_exactly_at_threshold_expires(self):
        """Journal memory at exactly the threshold is expired."""
        config = DecayConfig(tier0_expiry_cycles=5)
        exact_time = NOW - timedelta(days=5)
        mem = _make_memory("Boundary journal", tier=MemoryTier.JOURNAL, last_reinforced=exact_time)

        result = apply_decay([mem], NOW, config)

        assert len(result.expirations) == 1


# ---------------------------------------------------------------------------
# Recency-based decay: Tier 1 (consolidated)
# ---------------------------------------------------------------------------


class TestTier1Decay:
    def test_tier1_decays_salience_then_expires(self):
        """Consolidated memory unreinforced for N cycles expires."""
        config = DecayConfig(tier1_decay_cycles=8)
        old_time = NOW - timedelta(days=9)
        mem = _make_memory("Old consolidated", tier=MemoryTier.CONSOLIDATED, last_reinforced=old_time, salience=4)

        result = apply_decay([mem], NOW, config)

        assert len(result.expirations) == 1
        assert result.expirations[0][0].title == "Old consolidated"

    def test_tier1_salience_reduced_at_half_threshold(self):
        """Salience drops by 1 when unreinforced for half the decay period."""
        config = DecayConfig(tier1_decay_cycles=8)
        # 4 days = half of 8 (tier1_decay_cycles // 2)
        half_time = NOW - timedelta(days=4)
        mem = _make_memory("Aging memory", tier=MemoryTier.CONSOLIDATED, last_reinforced=half_time, salience=4)

        result = apply_decay([mem], NOW, config)

        assert len(result.survivors) == 1
        assert result.survivors[0][0].salience == 3
        # Verify event was logged
        sal_events = [e for e in result.events if e.action == "salience_reduced"]
        assert len(sal_events) == 1

    def test_tier1_salience_floors_at_1(self):
        """Salience never goes below 1."""
        config = DecayConfig(tier1_decay_cycles=8)
        half_time = NOW - timedelta(days=5)
        mem = _make_memory("Low salience", tier=MemoryTier.CONSOLIDATED, last_reinforced=half_time, salience=1)

        result = apply_decay([mem], NOW, config)

        assert len(result.survivors) == 1
        # Salience stays at 1 — no salience_reduced event since value didn't change
        assert result.survivors[0][0].salience == 1
        sal_events = [e for e in result.events if e.action == "salience_reduced"]
        assert len(sal_events) == 0

    def test_tier1_survives_when_reinforced(self):
        """Consolidated memory with recent reinforcement survives unchanged."""
        config = DecayConfig(tier1_decay_cycles=8)
        recent = NOW - timedelta(days=1)
        mem = _make_memory("Fresh consolidated", tier=MemoryTier.CONSOLIDATED, last_reinforced=recent, salience=4)

        result = apply_decay([mem], NOW, config)

        assert len(result.survivors) == 1
        assert result.survivors[0][0].salience == 4
        assert len(result.events) == 0


# ---------------------------------------------------------------------------
# Recency-based decay: Tier 2 (core)
# ---------------------------------------------------------------------------


class TestTier2Decay:
    def test_tier2_demotes_to_tier1_when_unreinforced(self):
        """Core memory unreinforced for M cycles demotes to consolidated."""
        config = DecayConfig(tier2_demote_cycles=10)
        old_time = NOW - timedelta(days=11)
        mem = _make_memory("Old core", tier=MemoryTier.CORE, last_reinforced=old_time, salience=5)

        result = apply_decay([mem], NOW, config)

        assert len(result.demotions) == 1
        demoted_fm, _, _, new_tier = result.demotions[0]
        assert demoted_fm.tier == MemoryTier.CONSOLIDATED
        assert new_tier == MemoryTier.CONSOLIDATED
        assert len(result.survivors) == 0

    def test_tier2_survives_when_reinforced(self):
        """Core memory with recent reinforcement stays in tier 2."""
        config = DecayConfig(tier2_demote_cycles=10)
        recent = NOW - timedelta(days=3)
        mem = _make_memory("Active core", tier=MemoryTier.CORE, last_reinforced=recent, salience=5)

        result = apply_decay([mem], NOW, config)

        assert len(result.survivors) == 1
        assert result.survivors[0][0].tier == MemoryTier.CORE


# ---------------------------------------------------------------------------
# Capacity pressure
# ---------------------------------------------------------------------------


class TestCapacityPressure:
    def test_tier2_capacity_pressure_demotes_least_recent(self):
        """When core count exceeds budget, oldest-reinforced memories demote."""
        config = DecayConfig(tier2_capacity=3, tier2_demote_cycles=100)

        memories = []
        for i in range(5):
            reinforced = NOW - timedelta(days=i)
            memories.append(
                _make_memory(
                    f"Core {i}",
                    tier=MemoryTier.CORE,
                    last_reinforced=reinforced,
                    salience=5,
                )
            )

        result = apply_decay(memories, NOW, config)

        # 5 cores, budget 3 → 2 demoted (the oldest two: Core 4, Core 3)
        assert len(result.demotions) == 2
        demoted_titles = {d[0].title for d in result.demotions}
        assert "Core 4" in demoted_titles
        assert "Core 3" in demoted_titles
        assert len(result.survivors) == 3

    def test_tier2_under_budget_no_pressure(self):
        """When core count is within budget, no capacity-driven demotion."""
        config = DecayConfig(tier2_capacity=15, tier2_demote_cycles=100)

        memories = [
            _make_memory(f"Core {i}", tier=MemoryTier.CORE, last_reinforced=NOW, salience=5)
            for i in range(10)
        ]

        result = apply_decay(memories, NOW, config)

        assert len(result.demotions) == 0
        assert len(result.survivors) == 10

    def test_capacity_and_recency_combine(self):
        """Capacity pressure selects among unreinforced memories first.

        When both recency demotion and capacity pressure apply, recency
        demotions happen first (in the recency pass), then capacity
        pressure applies to the remaining survivors.
        """
        config = DecayConfig(tier2_capacity=2, tier2_demote_cycles=10)

        # 1 very old (will be recency-demoted), 3 medium-age (under threshold)
        memories = [
            _make_memory("Very old", tier=MemoryTier.CORE, last_reinforced=NOW - timedelta(days=15), salience=5),
            _make_memory("Medium old", tier=MemoryTier.CORE, last_reinforced=NOW - timedelta(days=5), salience=5),
            _make_memory("Somewhat old", tier=MemoryTier.CORE, last_reinforced=NOW - timedelta(days=3), salience=5),
            _make_memory("Recent", tier=MemoryTier.CORE, last_reinforced=NOW - timedelta(days=1), salience=5),
        ]

        result = apply_decay(memories, NOW, config)

        # "Very old" demoted by recency (15 days > 10 threshold)
        # Remaining: 3 cores, budget 2 → "Medium old" demoted by capacity
        assert len(result.demotions) == 2
        demoted_titles = {d[0].title for d in result.demotions}
        assert "Very old" in demoted_titles
        assert "Medium old" in demoted_titles
        assert len(result.survivors) == 2


# ---------------------------------------------------------------------------
# Reinforcement signals
# ---------------------------------------------------------------------------


class TestReinforcementSignals:
    def test_touch_events_update_last_reinforced(self):
        """Memories touched via `ve entity touch` have updated timestamps that prevent decay.

        Touch updates last_reinforced, so a recently-touched memory should
        survive even if it was created long ago.
        """
        config = DecayConfig(tier2_demote_cycles=10)
        # Created long ago, but touched recently
        mem = _make_memory(
            "Touched core",
            tier=MemoryTier.CORE,
            last_reinforced=NOW - timedelta(days=2),  # recently touched
            salience=5,
        )

        result = apply_decay([mem], NOW, config)

        assert len(result.survivors) == 1
        assert result.survivors[0][0].title == "Touched core"

    def test_consolidation_reinforcement_prevents_decay(self):
        """Memories reinforced during consolidation (updated last_reinforced) resist decay."""
        config = DecayConfig(tier1_decay_cycles=8)
        # Reinforced during this cycle (last_reinforced = now)
        mem = _make_memory(
            "Just consolidated",
            tier=MemoryTier.CONSOLIDATED,
            last_reinforced=NOW,
            salience=4,
        )

        result = apply_decay([mem], NOW, config)

        assert len(result.survivors) == 1
        assert len(result.events) == 0


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


class TestDecayAuditEvents:
    def test_decay_produces_audit_events(self):
        """Decay returns DecayEvent objects describing what was decayed and why."""
        config = DecayConfig(tier0_expiry_cycles=5, tier1_decay_cycles=8, tier2_demote_cycles=10)

        memories = [
            _make_memory("Expired journal", tier=MemoryTier.JOURNAL, last_reinforced=NOW - timedelta(days=6)),
            _make_memory("Expired consolidated", tier=MemoryTier.CONSOLIDATED, last_reinforced=NOW - timedelta(days=9)),
            _make_memory("Demoted core", tier=MemoryTier.CORE, last_reinforced=NOW - timedelta(days=12)),
            _make_memory("Survivor", tier=MemoryTier.CORE, last_reinforced=NOW),
        ]

        result = apply_decay(memories, NOW, config)

        assert len(result.events) == 3

        # Check each event has required fields
        for event in result.events:
            assert event.timestamp == NOW
            assert event.memory_title
            assert event.memory_id
            assert event.action in ("expired", "demoted", "salience_reduced")
            assert event.from_tier
            assert event.reason

        # Verify specific events
        actions = {e.memory_title: e.action for e in result.events}
        assert actions["Expired journal"] == "expired"
        assert actions["Expired consolidated"] == "expired"
        assert actions["Demoted core"] == "demoted"


# ---------------------------------------------------------------------------
# Boundedness simulation (20+ cycles)
# ---------------------------------------------------------------------------


class TestBoundednessSimulation:
    def test_20_cycle_simulation_stays_bounded(self):
        """Simulate 20+ consolidation cycles and verify memory stays bounded.

        Each cycle adds new journal memories. Some themes recur (getting
        promoted to consolidated/core), while one-off themes fade.
        The core count must never exceed tier2_capacity and the startup
        payload must stay under 4K tokens (~16K chars).
        """
        config = DecayConfig(
            tier0_expiry_cycles=5,
            tier1_decay_cycles=8,
            tier2_demote_cycles=10,
            tier2_capacity=15,
            tier1_capacity=30,
        )

        # In-memory state: list of (fm, content, path) tuples
        all_memories: list[tuple[MemoryFrontmatter, str, Path]] = []
        memory_counter = 0

        # Themes that recur every cycle (should become core)
        recurring_themes = [
            "Template editing workflow",
            "Verify state before acting",
            "Use uv run for dev",
            "Check PR status first",
            "Commit chunks with code",
        ]

        # One-off themes (should eventually decay)
        one_off_themes = [
            "Debug session {cycle}",
            "Meeting note {cycle}",
            "Observation {cycle}",
            "Experiment {cycle}",
            "Quick fix {cycle}",
            "Config tweak {cycle}",
            "Log analysis {cycle}",
            "Random thought {cycle}",
        ]

        for cycle in range(25):
            cycle_time = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=cycle)

            # Add one-off journals (unique per cycle)
            for template in one_off_themes:
                memory_counter += 1
                title = template.format(cycle=cycle)
                fm = MemoryFrontmatter(
                    title=title,
                    category=MemoryCategory.DOMAIN,
                    valence=MemoryValence.NEUTRAL,
                    salience=2,
                    tier=MemoryTier.JOURNAL,
                    last_reinforced=cycle_time,
                    recurrence_count=0,
                )
                path = Path(f"/fake/journal/mem_{memory_counter}.md")
                all_memories.append((fm, f"Content for {title}", path))

            # Simulate consolidation for recurring themes:
            # If an existing consolidated/core memory with this title exists,
            # reinforce it (update last_reinforced, bump recurrence_count).
            # Otherwise, create a new consolidated memory.
            for theme in recurring_themes:
                existing_idx = None
                for i, (fm, content, path) in enumerate(all_memories):
                    if fm.title == theme and fm.tier in (MemoryTier.CONSOLIDATED, MemoryTier.CORE):
                        existing_idx = i
                        break

                if existing_idx is not None:
                    old_fm, old_content, old_path = all_memories[existing_idx]
                    reinforced = old_fm.model_copy(
                        update={
                            "recurrence_count": old_fm.recurrence_count + 1,
                            "last_reinforced": cycle_time,
                        }
                    )
                    all_memories[existing_idx] = (reinforced, old_content, old_path)
                else:
                    memory_counter += 1
                    fm = MemoryFrontmatter(
                        title=theme,
                        category=MemoryCategory.SKILL,
                        valence=MemoryValence.NEUTRAL,
                        salience=4,
                        tier=MemoryTier.CONSOLIDATED,
                        last_reinforced=cycle_time,
                        recurrence_count=1,
                    )
                    path = Path(f"/fake/consolidated/mem_{memory_counter}.md")
                    all_memories.append((fm, f"Content for {theme}", path))

            # Promote high-recurrence consolidated to core
            new_all = []
            for fm, content, path in all_memories:
                if fm.tier == MemoryTier.CONSOLIDATED and fm.recurrence_count >= 3:
                    promoted = fm.model_copy(
                        update={
                            "tier": MemoryTier.CORE,
                            "salience": 5,
                        }
                    )
                    new_path = Path(f"/fake/core/{path.stem}.md")
                    new_all.append((promoted, content, new_path))
                else:
                    new_all.append((fm, content, path))
            all_memories = new_all

            # Apply decay
            decay_result = apply_decay(all_memories, cycle_time, config)

            # Apply decisions
            new_memories = list(decay_result.survivors)
            for fm, content, path, new_tier in decay_result.demotions:
                new_path = Path(f"/fake/{new_tier.value}/{path.stem}.md")
                new_memories.append((fm, content, new_path))
            # Expirations are dropped

            all_memories = new_memories

        # --- Assertions ---

        # Count by tier
        core_count = sum(1 for fm, _, _ in all_memories if fm.tier == MemoryTier.CORE)
        consolidated_count = sum(1 for fm, _, _ in all_memories if fm.tier == MemoryTier.CONSOLIDATED)
        journal_count = sum(1 for fm, _, _ in all_memories if fm.tier == MemoryTier.JOURNAL)

        # Core must not exceed capacity
        assert core_count <= config.tier2_capacity, (
            f"Core count {core_count} exceeds budget {config.tier2_capacity}"
        )

        # Startup payload: core content + consolidated titles
        core_payload = sum(
            len(content) + len(fm.title)
            for fm, content, _ in all_memories
            if fm.tier == MemoryTier.CORE
        )
        consolidated_titles_payload = sum(
            len(fm.title)
            for fm, _, _ in all_memories
            if fm.tier == MemoryTier.CONSOLIDATED
        )
        total_payload_chars = core_payload + consolidated_titles_payload
        total_payload_tokens = total_payload_chars / 4  # ~4 chars/token heuristic

        assert total_payload_tokens <= 4096, (
            f"Startup payload {total_payload_tokens:.0f} tokens exceeds 4K budget"
        )

        # At least some recurring themes survived as core
        core_titles = {fm.title for fm, _, _ in all_memories if fm.tier == MemoryTier.CORE}
        survived_recurring = core_titles & set(recurring_themes)
        assert len(survived_recurring) >= 3, (
            f"Expected at least 3 recurring themes in core, got {len(survived_recurring)}: {survived_recurring}"
        )

        # One-off themes from early cycles should have expired
        # (they were journal tier and unreinforced for many cycles)
        surviving_titles = {fm.title for fm, _, _ in all_memories}
        early_oneoffs = {t.format(cycle=0) for t in one_off_themes}
        assert not (early_oneoffs & surviving_titles), (
            f"Early one-off themes should have decayed: {early_oneoffs & surviving_titles}"
        )
