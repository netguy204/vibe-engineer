"""Memory decay mechanics for entity memory tiers.

# Chunk: docs/chunks/entity_memory_decay

Implements two complementary decay mechanisms that run as a post-consolidation
step to bound memory growth:

1. **Recency-based decay**: Memories unreinforced for N cycles lose salience,
   demote, or expire depending on their tier.
2. **Capacity pressure**: When a tier exceeds its soft budget, the
   least-recently-reinforced memories are demoted or expired first.

The core function `apply_decay()` is a pure function: memories in, decisions
out. The caller (run_consolidation) applies the decisions to disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from models.entity import DecayConfig, DecayEvent, MemoryFrontmatter, MemoryTier


@dataclass
class DecayResult:
    """Result of applying decay to a set of memories.

    Contains the full set of decisions: which memories survive, which are
    demoted, and which are expired. Also carries audit events for logging.
    """

    survivors: list[tuple[MemoryFrontmatter, str, Path]] = field(default_factory=list)
    demotions: list[tuple[MemoryFrontmatter, str, Path, MemoryTier]] = field(
        default_factory=list
    )  # (fm, content, path, new_tier)
    expirations: list[tuple[MemoryFrontmatter, str, Path]] = field(default_factory=list)
    events: list[DecayEvent] = field(default_factory=list)


# Chunk: docs/chunks/entity_memory_decay
def apply_decay(
    memories: list[tuple[MemoryFrontmatter, str, Path]],
    current_cycle: datetime,
    config: DecayConfig,
) -> DecayResult:
    """Apply recency-based decay and capacity pressure to a set of memories.

    This is a pure function — it takes memory data and returns decisions.
    The caller applies the decisions to disk.

    Args:
        memories: List of (frontmatter, content, file_path) tuples.
        current_cycle: Current timestamp (typically now).
        config: Decay configuration parameters.

    Returns:
        DecayResult with survivors, demotions, expirations, and audit events.
    """
    result = DecayResult()

    # Partition by tier for processing
    tier0: list[tuple[MemoryFrontmatter, str, Path]] = []
    tier1: list[tuple[MemoryFrontmatter, str, Path]] = []
    tier2: list[tuple[MemoryFrontmatter, str, Path]] = []

    for mem in memories:
        fm = mem[0]
        if fm.tier == MemoryTier.JOURNAL:
            tier0.append(mem)
        elif fm.tier == MemoryTier.CONSOLIDATED:
            tier1.append(mem)
        elif fm.tier == MemoryTier.CORE:
            tier2.append(mem)

    # --- Recency-based decay pass ---

    # Tier 0: expire after tier0_expiry_cycles days without reinforcement
    for fm, content, path in tier0:
        days_since = (current_cycle - fm.last_reinforced).days
        if days_since >= config.tier0_expiry_cycles:
            result.expirations.append((fm, content, path))
            result.events.append(
                DecayEvent(
                    timestamp=current_cycle,
                    memory_title=fm.title,
                    memory_id=path.stem,
                    action="expired",
                    from_tier=fm.tier.value,
                    to_tier=None,
                    reason=f"unreinforced for {days_since} cycles (threshold: {config.tier0_expiry_cycles})",
                )
            )
        else:
            result.survivors.append((fm, content, path))

    # Tier 1: reduce salience at half the decay threshold, expire at full threshold
    for fm, content, path in tier1:
        days_since = (current_cycle - fm.last_reinforced).days
        if days_since >= config.tier1_decay_cycles:
            result.expirations.append((fm, content, path))
            result.events.append(
                DecayEvent(
                    timestamp=current_cycle,
                    memory_title=fm.title,
                    memory_id=path.stem,
                    action="expired",
                    from_tier=fm.tier.value,
                    to_tier=None,
                    reason=f"unreinforced for {days_since} cycles (threshold: {config.tier1_decay_cycles})",
                )
            )
        elif days_since >= config.tier1_decay_cycles // 2:
            # Reduce salience but keep the memory
            new_salience = max(1, fm.salience - 1)
            if new_salience < fm.salience:
                # Create a copy with reduced salience
                updated_fm = fm.model_copy(update={"salience": new_salience})
                result.survivors.append((updated_fm, content, path))
                result.events.append(
                    DecayEvent(
                        timestamp=current_cycle,
                        memory_title=fm.title,
                        memory_id=path.stem,
                        action="salience_reduced",
                        from_tier=fm.tier.value,
                        to_tier=fm.tier.value,
                        reason=f"unreinforced for {days_since} cycles, salience {fm.salience} → {new_salience}",
                    )
                )
            else:
                result.survivors.append((fm, content, path))
        else:
            result.survivors.append((fm, content, path))

    # Tier 2: demote to tier 1 after tier2_demote_cycles without reinforcement
    surviving_tier2: list[tuple[MemoryFrontmatter, str, Path]] = []
    for fm, content, path in tier2:
        days_since = (current_cycle - fm.last_reinforced).days
        if days_since >= config.tier2_demote_cycles:
            demoted_fm = fm.model_copy(update={"tier": MemoryTier.CONSOLIDATED})
            result.demotions.append((demoted_fm, content, path, MemoryTier.CONSOLIDATED))
            result.events.append(
                DecayEvent(
                    timestamp=current_cycle,
                    memory_title=fm.title,
                    memory_id=path.stem,
                    action="demoted",
                    from_tier=MemoryTier.CORE.value,
                    to_tier=MemoryTier.CONSOLIDATED.value,
                    reason=f"unreinforced for {days_since} cycles (threshold: {config.tier2_demote_cycles})",
                )
            )
        else:
            surviving_tier2.append((fm, content, path))

    # --- Capacity pressure pass (tier 2 only, after recency pass) ---
    if len(surviving_tier2) > config.tier2_capacity:
        # Sort by last_reinforced ascending (oldest first = demote first)
        surviving_tier2.sort(key=lambda m: m[0].last_reinforced)
        excess = len(surviving_tier2) - config.tier2_capacity

        for fm, content, path in surviving_tier2[:excess]:
            demoted_fm = fm.model_copy(update={"tier": MemoryTier.CONSOLIDATED})
            result.demotions.append((demoted_fm, content, path, MemoryTier.CONSOLIDATED))
            result.events.append(
                DecayEvent(
                    timestamp=current_cycle,
                    memory_title=fm.title,
                    memory_id=path.stem,
                    action="demoted",
                    from_tier=MemoryTier.CORE.value,
                    to_tier=MemoryTier.CONSOLIDATED.value,
                    reason=f"capacity pressure: {len(surviving_tier2)}/{config.tier2_capacity} core memories",
                )
            )

        # Remaining tier2 memories survive
        for fm, content, path in surviving_tier2[excess:]:
            result.survivors.append((fm, content, path))
    else:
        result.survivors.extend(surviving_tier2)

    return result
