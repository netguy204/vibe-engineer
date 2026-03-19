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
