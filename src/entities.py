"""Entities domain class for managing long-running agent personas with persistent memory.

# Chunk: docs/chunks/entity_memory_schema

Entities are named, long-running agent personas that accumulate understanding
across sessions. Unlike workflow artifacts (chunks, narratives, etc.), entities
live under `.entities/` at the project root and represent runtime state for
agent personas — not documentation artifacts.

Directory structure:
    .entities/
      <name>/
        identity.md         # Entity role, startup instructions
        memories/
          journal/          # Tier 0: raw session memories
          consolidated/     # Tier 1: cross-session patterns
          core/             # Tier 2: persistent skills
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from frontmatter import parse_frontmatter, update_frontmatter_field
from models.entity import (
    ENTITY_NAME_PATTERN,
    EntityIdentity,
    MemoryFrontmatter,
    MemoryTier,
    TouchEvent,
)
from template_system import render_template


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug[:60]  # Limit length


class Entities:
    """Manages entity lifecycle and memory storage.

    Entities live under `.entities/` at the project root. Each entity has
    an identity file and a three-tier memory directory structure.
    """

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir

    @property
    def entities_dir(self) -> Path:
        """Root directory for all entities."""
        return self._project_dir / ".entities"

    def entity_dir(self, name: str) -> Path:
        """Directory for a specific entity."""
        return self.entities_dir / name

    def entity_exists(self, name: str) -> bool:
        """Check if an entity exists."""
        return self.entity_dir(name).is_dir()

    def list_entities(self) -> list[str]:
        """List all entity names."""
        if not self.entities_dir.exists():
            return []
        return sorted(
            d.name
            for d in self.entities_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    def create_entity(self, name: str, role: str | None = None) -> Path:
        """Create a new entity with directory structure and identity file.

        Args:
            name: Entity name (lowercase alphanumeric + underscores).
            role: Optional brief description of entity's purpose.

        Returns:
            Path to the created entity directory.

        Raises:
            ValueError: If entity already exists or name is invalid.
        """
        # Validate name
        if not ENTITY_NAME_PATTERN.match(name):
            raise ValueError(
                f"Invalid entity name '{name}': must be lowercase, start with a letter, "
                "and contain only letters, digits, and underscores"
            )

        entity_path = self.entity_dir(name)
        if entity_path.exists():
            raise ValueError(f"Entity '{name}' already exists at {entity_path}")

        # Create directory structure
        entity_path.mkdir(parents=True)
        memories_dir = entity_path / "memories"
        for tier in MemoryTier:
            (memories_dir / tier.value).mkdir(parents=True)

        # Render identity.md from template
        created = datetime.now(timezone.utc).isoformat()
        identity_content = render_template(
            "entity",
            "identity.md.jinja2",
            name=name,
            role=role,
            created=created,
        )
        (entity_path / "identity.md").write_text(identity_content)

        return entity_path

    def parse_identity(self, name: str) -> EntityIdentity | None:
        """Parse an entity's identity.md frontmatter.

        Returns:
            EntityIdentity if parsing succeeds, None otherwise.
        """
        identity_path = self.entity_dir(name) / "identity.md"
        return parse_frontmatter(identity_path, EntityIdentity)

    def list_memories(
        self, name: str, tier: MemoryTier | None = None
    ) -> list[MemoryFrontmatter]:
        """List memory frontmatter for an entity, optionally filtered by tier.

        Args:
            name: Entity name.
            tier: Optional tier filter. If None, returns all tiers.

        Returns:
            List of MemoryFrontmatter instances.
        """
        memories_dir = self.entity_dir(name) / "memories"
        if not memories_dir.exists():
            return []

        tiers = [tier] if tier else list(MemoryTier)
        results = []

        for t in tiers:
            tier_dir = memories_dir / t.value
            if not tier_dir.exists():
                continue
            for f in sorted(tier_dir.glob("*.md")):
                fm, _ = self.parse_memory(f)
                if fm:
                    results.append(fm)

        return results

    def get_memory_path(self, name: str, tier: MemoryTier, memory_id: str) -> Path:
        """Get the path to a specific memory file.

        Args:
            name: Entity name.
            tier: Memory tier.
            memory_id: Memory filename (without .md extension).

        Returns:
            Path to the memory file.
        """
        return self.entity_dir(name) / "memories" / tier.value / f"{memory_id}.md"

    def memory_index(self, name: str) -> dict:
        """Build a startup memory index for an entity.

        Returns all core memories in full and consolidated memory titles only.
        This is the payload loaded at entity startup.

        Args:
            name: Entity name.

        Returns:
            Dict with 'core' (full MemoryFrontmatter + content) and
            'consolidated' (titles only) keys.
        """
        memories_dir = self.entity_dir(name) / "memories"
        index: dict[str, Any] = {"core": [], "consolidated": []}

        # Core memories: full content
        core_dir = memories_dir / MemoryTier.CORE.value
        if core_dir.exists():
            for f in sorted(core_dir.glob("*.md")):
                fm, content = self.parse_memory(f)
                if fm:
                    index["core"].append({
                        "frontmatter": fm.model_dump(mode="json"),
                        "content": content,
                    })

        # Consolidated memories: titles only
        consolidated_dir = memories_dir / MemoryTier.CONSOLIDATED.value
        if consolidated_dir.exists():
            for f in sorted(consolidated_dir.glob("*.md")):
                fm, _ = self.parse_memory(f)
                if fm:
                    index["consolidated"].append(fm.title)

        return index

    def write_memory(
        self, entity_name: str, memory: MemoryFrontmatter, content: str
    ) -> Path:
        """Write a memory file for an entity.

        Generates a filename from timestamp + slugified title and writes
        the memory as a markdown file with YAML frontmatter.

        Args:
            entity_name: Entity name.
            memory: Memory frontmatter data.
            content: Free-text memory content.

        Returns:
            Path to the created memory file.
        """
        tier_dir = self.entity_dir(entity_name) / "memories" / memory.tier.value
        tier_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename: timestamp_slug.md
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        slug = _slugify(memory.title)
        filename = f"{timestamp}_{slug}.md"
        file_path = tier_dir / filename

        # Serialize frontmatter
        fm_dict = memory.model_dump(mode="json")
        # Convert datetime to ISO string for YAML
        if isinstance(fm_dict.get("last_reinforced"), str):
            pass  # Already serialized by mode="json"

        frontmatter_yaml = yaml.dump(fm_dict, default_flow_style=False, sort_keys=False)
        file_content = f"---\n{frontmatter_yaml}---\n\n{content}\n"
        file_path.write_text(file_content)

        return file_path

    def parse_memory(self, file_path: Path) -> tuple[MemoryFrontmatter | None, str]:
        """Parse a memory file into frontmatter and content.

        Args:
            file_path: Path to the memory markdown file.

        Returns:
            Tuple of (MemoryFrontmatter or None, content string).
        """
        if not file_path.exists():
            return None, ""

        text = file_path.read_text()

        # Split frontmatter and body
        import re as _re

        match = _re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, _re.DOTALL)
        if not match:
            return None, text

        try:
            fm_data = yaml.safe_load(match.group(1))
            if not isinstance(fm_data, dict):
                return None, text
            fm = MemoryFrontmatter.model_validate(fm_data)
            body = match.group(2).strip()
            return fm, body
        except Exception:
            return None, text

    def update_memory_field(
        self, file_path: Path, field: str, value: Any
    ) -> None:
        """Update a single frontmatter field in a memory file.

        Args:
            file_path: Path to the memory file.
            field: Frontmatter field name to update.
            value: New value for the field.
        """
        update_frontmatter_field(file_path, field, value)

    # Chunk: docs/chunks/entity_touch_command
    def find_memory(self, entity_name: str, memory_id: str) -> Path | None:
        """Find a memory file by its filename stem across all tiers.

        Searches core → consolidated → journal (core is the expected tier
        for touch commands, so we check it first for performance).

        Args:
            entity_name: Entity name.
            memory_id: Filename stem (without .md extension) of the memory.

        Returns:
            Path to the memory file if found, None otherwise.
        """
        memories_dir = self.entity_dir(entity_name) / "memories"
        # Search order: core first (most common for touch), then consolidated, then journal
        for tier in [MemoryTier.CORE, MemoryTier.CONSOLIDATED, MemoryTier.JOURNAL]:
            candidate = memories_dir / tier.value / f"{memory_id}.md"
            if candidate.exists():
                return candidate
        return None

    # Chunk: docs/chunks/entity_touch_command
    def touch_memory(
        self, entity_name: str, memory_id: str, reason: str | None = None
    ) -> TouchEvent:
        """Record a touch event for a memory, updating last_reinforced and appending to the touch log.

        Args:
            entity_name: Entity name.
            memory_id: Filename stem of the memory to touch.
            reason: Optional reason the memory was useful.

        Returns:
            The TouchEvent that was recorded.

        Raises:
            ValueError: If entity doesn't exist or memory_id is not found.
        """
        if not self.entity_exists(entity_name):
            raise ValueError(f"Entity '{entity_name}' does not exist")

        memory_path = self.find_memory(entity_name, memory_id)
        if memory_path is None:
            raise ValueError(
                f"Memory '{memory_id}' not found for entity '{entity_name}'"
            )

        # Parse memory to get its title
        fm, _ = self.parse_memory(memory_path)
        if fm is None:
            raise ValueError(
                f"Could not parse memory file at {memory_path}"
            )

        # Update last_reinforced
        now = datetime.now(timezone.utc)
        self.update_memory_field(memory_path, "last_reinforced", now.isoformat())

        # Create the touch event
        event = TouchEvent(
            timestamp=now,
            memory_id=memory_id,
            memory_title=fm.title,
            reason=reason,
        )

        # Append to touch log
        touch_log_path = self.entity_dir(entity_name) / "touch_log.jsonl"
        with open(touch_log_path, "a") as f:
            f.write(event.model_dump_json() + "\n")

        return event

    # Chunk: docs/chunks/entity_touch_command
    def read_touch_log(self, entity_name: str) -> list[TouchEvent]:
        """Read all touch events from an entity's touch log.

        Args:
            entity_name: Entity name.

        Returns:
            List of TouchEvent instances in chronological order.
        """
        touch_log_path = self.entity_dir(entity_name) / "touch_log.jsonl"
        if not touch_log_path.exists():
            return []

        events = []
        for line in touch_log_path.read_text().splitlines():
            line = line.strip()
            if line:
                events.append(TouchEvent.model_validate_json(line))
        return events
