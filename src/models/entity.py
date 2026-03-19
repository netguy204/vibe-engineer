"""Entity domain models for long-running agent personas with persistent memory.

# Chunk: docs/chunks/entity_memory_schema
"""

import re
from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Entity name validation: lowercase alphanumeric + underscores, must start with letter
ENTITY_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class MemoryTier(StrEnum):
    """Memory tier levels following the LSTM-inspired consolidation model."""

    JOURNAL = "journal"  # Tier 0: raw session memories, high volume, ephemeral
    CONSOLIDATED = "consolidated"  # Tier 1: cross-session patterns, merged and refined
    CORE = "core"  # Tier 2: persistent skills, loaded at every startup


class MemoryCategory(StrEnum):
    """Categories of memory from the agent memory investigation taxonomy."""

    CORRECTION = "correction"
    SKILL = "skill"
    DOMAIN = "domain"
    CONFIRMATION = "confirmation"
    COORDINATION = "coordination"
    AUTONOMY = "autonomy"


class MemoryValence(StrEnum):
    """Emotional valence of a memory."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class MemoryFrontmatter(BaseModel):
    """Frontmatter schema for memory files.

    Each memory is a markdown file with YAML frontmatter containing these
    structured fields, plus free-text content in the body.
    """

    title: str = Field(description="Short title (3-8 words)")
    category: MemoryCategory
    valence: MemoryValence
    salience: int = Field(ge=1, le=5, description="Importance level: 1 (low) to 5 (critical)")
    tier: MemoryTier
    last_reinforced: datetime = Field(description="ISO 8601 timestamp of last reinforcement")
    recurrence_count: int = Field(ge=0, description="How many times this pattern was observed")
    source_memories: list[str] = Field(
        default_factory=list,
        description="Titles of memories this was consolidated from (empty for tier 0)",
    )


class EntityIdentity(BaseModel):
    """Frontmatter schema for entity identity.md files."""

    name: str = Field(description="Entity name (lowercase alphanumeric + underscores)")
    role: str | None = Field(default=None, description="Brief description of entity's purpose")
    created: datetime

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate entity name: lowercase, starts with letter, alphanumeric + underscores."""
        if not ENTITY_NAME_PATTERN.match(v):
            raise ValueError(
                "Entity name must be lowercase, start with a letter, "
                "and contain only letters, digits, and underscores"
            )
        return v


# Chunk: docs/chunks/entity_touch_command
class TouchEvent(BaseModel):
    """A touch event recording runtime reinforcement of a memory.

    Touch events are appended to a JSONL touch log when an agent signals
    that a memory was actively useful during its workday.
    """

    timestamp: datetime = Field(description="When the touch occurred")
    memory_id: str = Field(description="Filename stem of the touched memory")
    memory_title: str = Field(description="Title from the memory's frontmatter")
    reason: Optional[str] = Field(default=None, description="Optional reason the memory was useful")


# Chunk: docs/chunks/entity_memory_decay
class DecayConfig(BaseModel):
    """Configuration for memory decay mechanics.

    Controls how aggressively memories are expired or demoted based on
    recency and capacity pressure. All cycle thresholds are measured in
    days since last reinforcement (each consolidation run ≈ 1 day).
    """

    tier0_expiry_cycles: int = Field(
        default=5,
        ge=1,
        description="Journal memories expire after this many cycles without association",
    )
    tier1_decay_cycles: int = Field(
        default=8,
        ge=1,
        description="Consolidated memories expire after this many cycles without reinforcement",
    )
    tier2_demote_cycles: int = Field(
        default=10,
        ge=1,
        description="Core memories demote to tier-1 after this many cycles without reinforcement",
    )
    tier2_capacity: int = Field(
        default=15,
        ge=1,
        description="Soft budget for core memories",
    )
    tier1_capacity: int = Field(
        default=30,
        ge=1,
        description="Soft budget for consolidated memories",
    )


# Chunk: docs/chunks/entity_memory_decay
class DecayEvent(BaseModel):
    """Audit log entry for a decay action taken on a memory.

    Appended to decay_log.jsonl after each consolidation cycle so the
    operator can audit what was forgotten and why.
    """

    timestamp: datetime = Field(description="When the decay action occurred")
    memory_title: str = Field(description="Title of the affected memory")
    memory_id: str = Field(description="Filename stem of the affected memory")
    action: str = Field(description="One of: expired, demoted, salience_reduced")
    from_tier: str = Field(description="Tier before the action")
    to_tier: Optional[str] = Field(
        default=None,
        description="Tier after the action (None for expiration)",
    )
    reason: str = Field(description="Human-readable explanation of why the action was taken")
