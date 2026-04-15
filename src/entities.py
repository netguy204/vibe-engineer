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
        wiki/               # Persistent structured knowledge base
          wiki_schema.md    # Schema and maintenance instructions
          identity.md       # Entity self-model
          index.md          # Content catalog
          log.md            # Chronological session log
          domain/           # Domain knowledge pages
          projects/         # Per-project working notes
          techniques/       # Approaches and patterns
          relationships/    # People, teams, other entities
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
    DecayEvent,
    EntityIdentity,
    MemoryFrontmatter,
    MemoryTier,
    SessionRecord,
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

        # Chunk: docs/chunks/entity_wiki_schema - Wiki directory initialization
        # Create wiki/ directory and subdirectories
        wiki_dir = entity_path / "wiki"
        wiki_dir.mkdir()
        for subdir in ["domain", "projects", "techniques", "relationships"]:
            (wiki_dir / subdir).mkdir()

        # Render wiki_schema.md (entity-agnostic — no variables)
        schema_content = render_template("entity", "wiki_schema.md.jinja2")
        (wiki_dir / "wiki_schema.md").write_text(schema_content)

        # Render initial wiki pages (receive name, role, created)
        for template_name, output_path in [
            ("wiki/identity.md.jinja2", wiki_dir / "identity.md"),
            ("wiki/index.md.jinja2", wiki_dir / "index.md"),
            ("wiki/log.md.jinja2", wiki_dir / "log.md"),
        ]:
            content = render_template(
                "entity", template_name, name=name, role=role, created=created
            )
            output_path.write_text(content)

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
                        "memory_id": f.stem,
                    })

        # Consolidated memories: title + category
        consolidated_dir = memories_dir / MemoryTier.CONSOLIDATED.value
        if consolidated_dir.exists():
            for f in sorted(consolidated_dir.glob("*.md")):
                fm, _ = self.parse_memory(f)
                if fm:
                    index["consolidated"].append({
                        "title": fm.title,
                        "category": fm.category.value if fm.category else None,
                    })

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

    # Chunk: docs/chunks/entity_startup_skill - Entity startup/wake payload
    def startup_payload(self, name: str) -> str:
        """Assemble the complete startup text payload for a named entity.

        This is the core "wake" logic — produces the context payload an agent
        needs to resume as a named entity, including identity, core memories,
        consolidated memory index, and the touch protocol instruction.

        Args:
            name: Entity name.

        Returns:
            Formatted text string containing all startup sections.

        Raises:
            ValueError: If the entity does not exist.
        """
        if not self.entity_exists(name):
            raise ValueError(f"Entity '{name}' does not exist")

        sections: list[str] = []

        # --- Identity ---
        identity = self.parse_identity(name)
        identity_path = self.entity_dir(name) / "identity.md"
        identity_body = self._read_body(identity_path)

        sections.append(f"# Entity: {name}")
        if identity and identity.role:
            sections.append(f"**Role:** {identity.role}")
        sections.append("")
        if identity_body:
            sections.append(identity_body)
            sections.append("")

        # --- Core Memories ---
        index = self.memory_index(name)
        core_dir = self.entity_dir(name) / "memories" / MemoryTier.CORE.value
        sections.append("## Core Memories")
        sections.append("")
        if index["core"]:
            for i, entry in enumerate(index["core"], 1):
                fm = entry["frontmatter"]
                content = entry["content"]
                memory_id = entry.get("memory_id", f"CM{i}")
                sections.append(f"### CM{i}: {fm['title']}")
                sections.append(f"*Category: {fm['category']} | ID: `{memory_id}`*")
                sections.append("")
                sections.append(content)
                sections.append("")
        else:
            sections.append("*No core memories yet.*")
            sections.append("")

        # --- Consolidated Memory Index ---
        sections.append("## Consolidated Memory Index")
        sections.append("")
        if index["consolidated"]:
            sections.append(
                "The following memories are available for on-demand retrieval "
                "via `ve entity recall`:"
            )
            sections.append("")
            for entry in index["consolidated"]:
                title = entry["title"]
                category = entry["category"]
                if category:
                    sections.append(f"- {title} ({category})")
                else:
                    sections.append(f"- {title}")
            sections.append("")
        else:
            sections.append("*No consolidated memories yet.*")
            sections.append("")

        # Chunk: docs/chunks/entity_touch_protocol_docs - Fix Touch Protocol command signature
        # --- Touch Protocol ---
        sections.append("## Touch Protocol")
        sections.append("")
        sections.append(
            "When you notice yourself applying a core memory, "
            "run `ve entity touch <name> <memory_id> \"<reason>\"` to reinforce it. "
            "Use the ID shown next to each core memory above (e.g., "
            "`ve entity touch <name> 20260319_core_memory \"applied this insight\"`). "
            "This enables retrieval-as-reinforcement — the act of noticing "
            "you used a memory strengthens it."
        )
        sections.append("")

        # --- Active State Reminders ---
        sections.append("## Active State")
        sections.append("")
        sections.append(
            "If you were previously watching channels or had pending async "
            "operations, restart them now."
        )
        sections.append("")

        return "\n".join(sections)

    # Chunk: docs/chunks/entity_startup_skill - Helper to extract markdown body content after frontmatter for identity loading
    def _read_body(self, file_path: Path) -> str:
        """Read the body content of a markdown file (after frontmatter).

        Args:
            file_path: Path to the markdown file.

        Returns:
            Body content string, or empty string if not parseable.
        """
        if not file_path.exists():
            return ""

        text = file_path.read_text()
        match = re.match(r"^---\s*\n.*?\n---\s*\n(.*)$", text, re.DOTALL)
        if not match:
            return text.strip()
        return match.group(1).strip()

    # Chunk: docs/chunks/entity_startup_skill - Entity recall for on-demand memory retrieval
    def recall_memory(
        self, name: str, query: str
    ) -> list[dict[str, Any]]:
        """Retrieve memories by title search (case-insensitive substring match).

        Searches core and consolidated memories for title matches. Journal
        memories are excluded from recall.

        Args:
            name: Entity name.
            query: Search string to match against memory titles.

        Returns:
            List of dicts with frontmatter, content, tier, and memory_id
            for each matching memory.

        Raises:
            ValueError: If the entity does not exist.
        """
        if not self.entity_exists(name):
            raise ValueError(f"Entity '{name}' does not exist")

        results: list[dict[str, Any]] = []
        query_lower = query.lower()
        memories_dir = self.entity_dir(name) / "memories"

        for tier in [MemoryTier.CORE, MemoryTier.CONSOLIDATED]:
            tier_dir = memories_dir / tier.value
            if not tier_dir.exists():
                continue
            for f in sorted(tier_dir.glob("*.md")):
                fm, content = self.parse_memory(f)
                if fm and query_lower in fm.title.lower():
                    results.append({
                        "frontmatter": fm.model_dump(mode="json"),
                        "content": content,
                        "tier": tier.value,
                        "memory_id": f.stem,
                    })

        return results

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

    # Chunk: docs/chunks/entity_memory_decay
    def append_decay_events(
        self, entity_name: str, events: list[DecayEvent]
    ) -> None:
        """Append decay events to the entity's decay log.

        Each event is serialized as a JSON line in decay_log.jsonl,
        providing an audit trail of what was forgotten and why.

        Args:
            entity_name: Entity name.
            events: List of DecayEvent instances to append.
        """
        if not events:
            return
        decay_log_path = self.entity_dir(entity_name) / "decay_log.jsonl"
        with open(decay_log_path, "a") as f:
            for event in events:
                f.write(event.model_dump_json() + "\n")

    # Chunk: docs/chunks/entity_memory_decay
    def read_decay_log(self, entity_name: str) -> list[DecayEvent]:
        """Read all decay events from an entity's decay log.

        Args:
            entity_name: Entity name.

        Returns:
            List of DecayEvent instances in chronological order.
        """
        decay_log_path = self.entity_dir(entity_name) / "decay_log.jsonl"
        if not decay_log_path.exists():
            return []

        events = []
        for line in decay_log_path.read_text().splitlines():
            line = line.strip()
            if line:
                events.append(DecayEvent.model_validate_json(line))
        return events

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

    # Chunk: docs/chunks/entity_session_tracking
    def append_session(self, entity_name: str, session_record: SessionRecord) -> None:
        """Append a session record to the entity's sessions log."""
        sessions_log_path = self.entity_dir(entity_name) / "sessions.jsonl"
        with open(sessions_log_path, "a") as f:
            f.write(session_record.model_dump_json() + "\n")

    # Chunk: docs/chunks/entity_session_tracking
    def list_sessions(self, entity_name: str) -> list[SessionRecord]:
        """Read all session records from the entity's sessions log."""
        sessions_log_path = self.entity_dir(entity_name) / "sessions.jsonl"
        if not sessions_log_path.exists():
            return []
        sessions = []
        for line in sessions_log_path.read_text().splitlines():
            line = line.strip()
            if line:
                sessions.append(SessionRecord.model_validate_json(line))
        return sessions

    # Chunk: docs/chunks/entity_session_tracking
    def archive_transcript(
        self,
        entity_name: str,
        session_id: str,
        project_path: str,
        claude_home: Path | None = None,
    ) -> bool:
        """Copy a Claude Code session transcript into entity storage.

        Args:
            entity_name: Entity name.
            session_id: UUID of the Claude Code session.
            project_path: Absolute path of the project (e.g. "/Users/btaylor/Projects/foo").
            claude_home: Override for ~/.claude (used in tests). Defaults to Path.home() / ".claude".

        Returns:
            True if the transcript was copied, False if source does not exist.
        """
        import shutil

        # Encode project_path to Claude Code's directory convention:
        # replace every '/' with '-' (the leading '/' becomes the leading '-')
        encoded = project_path.replace("/", "-")
        if claude_home is None:
            claude_home = Path.home() / ".claude"
        source = claude_home / "projects" / encoded / f"{session_id}.jsonl"

        if not source.exists():
            return False

        sessions_dir = self.entity_dir(entity_name) / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        destination = sessions_dir / f"{session_id}.jsonl"
        shutil.copy2(source, destination)
        return True
