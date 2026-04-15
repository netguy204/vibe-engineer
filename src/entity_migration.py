"""Entity migration: convert legacy .entities/ format to wiki-based git repo.

# Chunk: docs/chunks/entity_memory_migration - Full entity migration orchestration

This module reads an existing entity from the legacy `.entities/<name>/`
directory structure and produces a new wiki-based git repo entity using
`create_entity_repo` from `entity_repo.py`. The migration uses the Anthropic
Messages API (following the pattern from `entity_shutdown.py`) to synthesize
memories into coherent wiki pages.

Legacy entity structure (migrated FROM):
    .entities/<uuid>/
    ├── identity.md                # YAML frontmatter: name, role, created
    ├── memories/
    │   ├── journal/*.md           # tier 0 — session-level memories
    │   ├── consolidated/*.md      # tier 1 — cross-session patterns
    │   └── core/*.md              # tier 2 — identity-level memories
    └── sessions/*.jsonl           # archived session transcripts

New entity repo structure (migrated TO):
    <name>/
    ├── ENTITY.md
    ├── wiki/
    │   ├── identity.md            # synthesized from core/correction/autonomy
    │   ├── index.md
    │   ├── log.md                 # journal entries → chronological log
    │   ├── wiki_schema.md
    │   ├── domain/*.md            # synthesized from domain-category memories
    │   ├── techniques/*.md        # synthesized from skill/confirmation memories
    │   └── relationships/*.md
    ├── memories/                  # legacy memories preserved here
    └── episodic/                  # sessions/*.jsonl copied here
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Chunk: docs/chunks/entity_anthropic_dependency - Guard anthropic import
try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None  # type: ignore[assignment]

from entity_repo import ENTITY_REPO_NAME_PATTERN, _git_commit_all, _run_git, create_entity_repo
from frontmatter import parse_frontmatter
from models.entity import EntityIdentity, MemoryCategory, MemoryFrontmatter, MemoryTier


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class LegacyMemory:
    """A single memory read from the legacy entity structure."""

    tier: MemoryTier
    frontmatter: MemoryFrontmatter
    content: str
    file_path: Path


@dataclass
class ClassifiedMemories:
    """Memories grouped into wiki-category buckets."""

    identity: list[LegacyMemory] = field(default_factory=list)
    """Core-tier memories + correction/autonomy category memories."""

    domain: list[LegacyMemory] = field(default_factory=list)
    """Domain-category memories."""

    techniques: list[LegacyMemory] = field(default_factory=list)
    """Skill/confirmation-category memories."""

    relationships: list[LegacyMemory] = field(default_factory=list)
    """Coordination-category memories."""

    log: list[LegacyMemory] = field(default_factory=list)
    """Journal-tier memories (chronological)."""

    unclassified: list[LegacyMemory] = field(default_factory=list)
    """Memories that do not fit any bucket."""


@dataclass
class MigrationResult:
    """Summary of a completed entity migration."""

    entity_name: str
    source_dir: Path
    dest_dir: Path
    wiki_pages_created: list[str]
    memories_preserved: int
    sessions_migrated: int
    unclassified_count: int


# ---------------------------------------------------------------------------
# Step 2: read_legacy_entity
# ---------------------------------------------------------------------------

_FRONTMATTER_BODY_RE = re.compile(r"^---\s*\n.*?\n---\s*\n(.*)$", re.DOTALL)

_TIER_DIR_MAP = {
    "journal": MemoryTier.JOURNAL,
    "consolidated": MemoryTier.CONSOLIDATED,
    "core": MemoryTier.CORE,
}


def read_legacy_entity(
    entity_dir: Path,
) -> tuple[EntityIdentity | None, str, list[LegacyMemory]]:
    """Read legacy entity structure into structured types.

    Args:
        entity_dir: Path to the legacy entity directory (e.g. `.entities/<uuid>/`).

    Returns:
        Tuple of (EntityIdentity|None, identity_body_text, list[LegacyMemory]).
        ``identity_body_text`` is the markdown body after frontmatter in identity.md.
        Returns gracefully with empty list when subdirectories are missing.
    """
    # --- Parse identity.md ---
    identity: EntityIdentity | None = None
    identity_body = ""
    identity_path = entity_dir / "identity.md"
    if identity_path.exists():
        identity = parse_frontmatter(identity_path, EntityIdentity)
        # Extract body text (everything after frontmatter)
        text = identity_path.read_text()
        match = _FRONTMATTER_BODY_RE.match(text)
        if match:
            identity_body = match.group(1).strip()
        else:
            identity_body = text.strip()

    # --- Walk memory tiers ---
    memories: list[LegacyMemory] = []
    memories_root = entity_dir / "memories"

    for tier_name, tier_enum in _TIER_DIR_MAP.items():
        tier_dir = memories_root / tier_name
        if not tier_dir.exists():
            continue
        for md_file in sorted(tier_dir.glob("*.md")):
            fm, content = _parse_memory_file(md_file)
            if fm is None:
                continue
            memories.append(
                LegacyMemory(
                    tier=tier_enum,
                    frontmatter=fm,
                    content=content,
                    file_path=md_file,
                )
            )

    return identity, identity_body, memories


def _parse_memory_file(file_path: Path) -> tuple[MemoryFrontmatter | None, str]:
    """Parse a memory markdown file into (MemoryFrontmatter, body)."""
    import yaml

    if not file_path.exists():
        return None, ""

    text = file_path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
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


# ---------------------------------------------------------------------------
# Step 3: classify_memories
# ---------------------------------------------------------------------------

_IDENTITY_CATEGORIES = {MemoryCategory.CORRECTION, MemoryCategory.AUTONOMY}
_TECHNIQUES_CATEGORIES = {MemoryCategory.SKILL, MemoryCategory.CONFIRMATION}


def classify_memories(memories: list[LegacyMemory]) -> ClassifiedMemories:
    """Group a flat list of LegacyMemory into wiki-category buckets.

    Classification rules (a memory may appear in multiple buckets):
    - identity: tier == CORE  OR  category in {CORRECTION, AUTONOMY}
    - domain:   category == DOMAIN
    - techniques: category in {SKILL, CONFIRMATION}
    - relationships: category == COORDINATION
    - log: tier == JOURNAL
    - unclassified: nothing matched above

    The ``log`` bucket is sorted chronologically by filename.
    """
    classified = ClassifiedMemories()

    for mem in memories:
        placed = False

        if mem.tier == MemoryTier.CORE or mem.frontmatter.category in _IDENTITY_CATEGORIES:
            classified.identity.append(mem)
            placed = True

        if mem.frontmatter.category == MemoryCategory.DOMAIN:
            classified.domain.append(mem)
            placed = True

        if mem.frontmatter.category in _TECHNIQUES_CATEGORIES:
            classified.techniques.append(mem)
            placed = True

        if mem.frontmatter.category == MemoryCategory.COORDINATION:
            classified.relationships.append(mem)
            placed = True

        if mem.tier == MemoryTier.JOURNAL:
            classified.log.append(mem)
            placed = True

        if not placed:
            classified.unclassified.append(mem)

    # Sort log entries by filename (timestamp-prefixed → chronological)
    classified.log.sort(key=lambda m: m.file_path.name)

    return classified


# ---------------------------------------------------------------------------
# Step 4: format_log_page (mechanical, no LLM)
# ---------------------------------------------------------------------------

_MAX_LOG_ENTRIES = 30  # truncation safety guard


def format_log_page(log_entries: list[LegacyMemory], created_date: str) -> str:
    """Convert journal-tier memories to chronological wiki/log.md content.

    Args:
        log_entries: Journal memories, expected to be sorted chronologically.
        created_date: ISO 8601 string used in the frontmatter ``created`` field.

    Returns:
        Full markdown content for wiki/log.md.
    """
    updated = datetime.now(timezone.utc).isoformat()
    header = (
        f"---\ntitle: Session Log\ncreated: {created_date}\nupdated: {updated}\n---\n\n"
        "# Session Log\n\n"
        "Chronological record of sessions. Add an entry at the end of each session.\n\n"
    )

    if not log_entries:
        placeholder = (
            "<!-- Add session entries below. Most recent session at the bottom. -->\n"
        )
        return header + placeholder

    # Group entries by date (from last_reinforced)
    from collections import defaultdict

    groups: dict[str, list[LegacyMemory]] = defaultdict(list)
    for mem in log_entries:
        date_str = mem.frontmatter.last_reinforced.strftime("%Y-%m-%d")
        groups[date_str].append(mem)

    sections = []
    for date_str in sorted(groups.keys()):
        section_lines = [f"## {date_str}\n"]
        for mem in groups[date_str]:
            title = mem.frontmatter.title
            content = mem.content.strip()
            section_lines.append(f"- **{title}**: {content}")
        sections.append("\n".join(section_lines))

    return header + "\n\n".join(sections) + "\n"


# ---------------------------------------------------------------------------
# Shared prompt utilities
# ---------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM JSON output."""
    text = text.strip()
    match = re.match(r"^```(?:json)?\s*\n(.*?)\n\s*```\s*$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _format_memories_for_prompt(memories: list[LegacyMemory]) -> str:
    """Format a list of memories as readable text for an LLM prompt."""
    if not memories:
        return "(none)"
    parts = []
    for i, mem in enumerate(memories, 1):
        parts.append(
            f"{i}. **{mem.frontmatter.title}** "
            f"[{mem.frontmatter.category.value}, tier={mem.tier.value}, "
            f"salience={mem.frontmatter.salience}]\n"
            f"   {mem.content}"
        )
    return "\n\n".join(parts)


def _truncate_by_salience(memories: list[LegacyMemory], max_count: int = 30) -> list[LegacyMemory]:
    """Return at most max_count memories, keeping the highest-salience ones."""
    if len(memories) <= max_count:
        return memories
    sorted_mems = sorted(memories, key=lambda m: m.frontmatter.salience, reverse=True)
    return sorted_mems[:max_count]


# ---------------------------------------------------------------------------
# Step 5: synthesize_identity_page
# ---------------------------------------------------------------------------

_IDENTITY_SYNTHESIS_PROMPT = """\
You are synthesizing the identity wiki page for an AI entity.

Entity name: {name}
Entity role: {role}

Below is the entity's accumulated memory, grouped into its most identity-defining
categories: core knowledge, corrections, and autonomy calibrations.

{memories_text}

Original identity description:
{identity_body}

---

Produce a `wiki/identity.md` page with the following structure:

```
---
title: Identity
created: {created_date}
updated: {updated_date}
---

# Identity

## Who I Am

## Role

## Working Style

## Values

## Hard-Won Lessons
```

Requirements:
- Use wikilinks `[[page_name]]` to reference concepts that should have their own pages.
- Keep the page focused — distill the essence of the entity, not a dump of raw memories.
- The "Hard-Won Lessons" section should capture failures, surprising discoveries, and corrected assumptions.
- Synthesize and organize — do not simply list memories verbatim.
- Return ONLY the markdown content for identity.md. No extra explanation.
"""


def synthesize_identity_page(
    identity: EntityIdentity | None,
    identity_body: str,
    memories: list[LegacyMemory],
    client: object,
) -> str:
    """Synthesize wiki/identity.md from identity memories using the LLM.

    Args:
        identity: Parsed EntityIdentity frontmatter (may be None).
        identity_body: Markdown body from the legacy identity.md.
        memories: List of identity-classified LegacyMemory objects.
        client: An ``anthropic.Anthropic`` client instance.

    Returns:
        Full markdown content for wiki/identity.md.

    Raises:
        RuntimeError: If the anthropic package is not installed.
    """
    if anthropic is None:
        raise RuntimeError("anthropic package not installed")

    name = identity.name if identity else "unknown"
    role = identity.role if (identity and identity.role) else "not specified"
    created_date = (
        identity.created.isoformat()
        if identity and identity.created
        else datetime.now(timezone.utc).isoformat()
    )
    updated_date = datetime.now(timezone.utc).isoformat()

    truncated = _truncate_by_salience(memories, 30)
    memories_text = _format_memories_for_prompt(truncated)

    prompt = _IDENTITY_SYNTHESIS_PROMPT.format(
        name=name,
        role=role,
        memories_text=memories_text,
        identity_body=identity_body or "(none)",
        created_date=created_date,
        updated_date=updated_date,
    )

    response = client.messages.create(  # type: ignore[attr-defined]
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Step 6: synthesize_knowledge_pages
# ---------------------------------------------------------------------------

_KNOWLEDGE_PAGES_PROMPT = """\
You are synthesizing wiki pages for an AI entity's knowledge base.

Wiki type: {wiki_type}
Directory: wiki/{wiki_type}/

Below are the entity's memories for this knowledge area:

{memories_text}

---

Group related memories into focused wiki pages (one concept per page) and return
a JSON array of objects. Each object must have:
- "filename": lowercase slug + ".md" (e.g., "proving_model.md")
- "content": full markdown content for that page

Page content requirements:
- YAML frontmatter with `title`, `created: {created_date}`, `updated: {updated_date}`
- Clear, focused content synthesizing related memories
- Use wikilinks `[[page_name]]` for cross-references
- Keep each page to one concept or closely related cluster

If there are very few memories (1-3), it is fine to produce a single page.
Return ONLY the JSON array. No other text.

Example output format:
```json
[
  {{
    "filename": "proving_model.md",
    "content": "---\\ntitle: Proving Model\\ncreated: {created_date}\\nupdated: {updated_date}\\n---\\n\\n# Proving Model\\n\\n..."
  }}
]
```
"""


def synthesize_knowledge_pages(
    memories: list[LegacyMemory],
    wiki_type: str,
    client: object,
) -> list[tuple[str, str]]:
    """Synthesize multiple wiki pages from classified memories using the LLM.

    Args:
        memories: Memories to synthesize into pages.
        wiki_type: "domain" or "techniques" — the target subdirectory.
        client: An ``anthropic.Anthropic`` client instance.

    Returns:
        List of (filename, content) tuples. Returns [] if ``memories`` is empty
        (no LLM call) or if the LLM response cannot be parsed.

    Raises:
        RuntimeError: If the anthropic package is not installed.
    """
    if anthropic is None:
        raise RuntimeError("anthropic package not installed")

    if not memories:
        return []

    truncated = _truncate_by_salience(memories, 30)
    memories_text = _format_memories_for_prompt(truncated)
    created_date = datetime.now(timezone.utc).isoformat()
    updated_date = created_date

    prompt = _KNOWLEDGE_PAGES_PROMPT.format(
        wiki_type=wiki_type,
        memories_text=memories_text,
        created_date=created_date,
        updated_date=updated_date,
    )

    response = client.messages.create(  # type: ignore[attr-defined]
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    cleaned = _strip_code_fences(raw)

    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        print(
            f"Warning: could not parse JSON response for {wiki_type} wiki pages",
            file=sys.stderr,
        )
        return []

    if not isinstance(data, list):
        return []

    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        filename = item.get("filename", "")
        content = item.get("content", "")
        if filename and content:
            result.append((filename, content))

    return result


# ---------------------------------------------------------------------------
# Step 7: migrate_entity
# ---------------------------------------------------------------------------

# Chunk: docs/chunks/entity_memory_migration - Full entity migration orchestration
def migrate_entity(
    source_dir: Path,
    dest_parent: Path,
    new_name: str,
    role: str | None = None,
) -> MigrationResult:
    """Migrate a legacy entity to the new wiki-based git repo structure.

    This is the main orchestration function. It:
    1. Validates inputs
    2. Reads the legacy entity
    3. Classifies memories into wiki buckets
    4. Creates a new entity repo
    5. Synthesizes wiki pages via LLM (if anthropic available)
    6. Preserves legacy memories in memories/
    7. Copies sessions to episodic/
    8. Commits the migration result

    Args:
        source_dir: Path to the legacy entity directory.
        dest_parent: Parent directory where the new entity repo will be created.
        new_name: Human-readable name for the new entity repo (kebab-case).
        role: Override entity role. If None, reads from identity.md.

    Returns:
        MigrationResult with summary statistics.

    Raises:
        ValueError: If source_dir doesn't exist or new_name is invalid.
    """
    # Step 1: Validate inputs
    if not source_dir.exists():
        raise ValueError(f"Source entity directory not found: {source_dir}")

    if not ENTITY_REPO_NAME_PATTERN.match(new_name):
        raise ValueError(
            f"Invalid entity name '{new_name}'. "
            "Name must start with a lowercase letter and contain only "
            "lowercase letters, digits, underscores, or hyphens."
        )

    # Step 2: Read legacy entity
    identity, identity_body, memories = read_legacy_entity(source_dir)

    # Resolve role
    effective_role = role
    if effective_role is None and identity is not None and identity.role:
        effective_role = identity.role

    # Step 3: Classify memories
    classified = classify_memories(memories)

    # Step 4: Create new entity repo (creates stub wiki pages + git init + initial commit)
    repo_path = create_entity_repo(dest_parent, new_name, role=effective_role)

    wiki_pages_created: list[str] = []
    created_date = datetime.now(timezone.utc).isoformat()

    # Step 5: Synthesize and overwrite wiki pages
    if anthropic is not None:
        client = anthropic.Anthropic()

        # 5a. wiki/identity.md — synthesize from identity memories + identity body
        identity_content = synthesize_identity_page(
            identity, identity_body, classified.identity, client
        )
        identity_page = repo_path / "wiki" / "identity.md"
        identity_page.write_text(identity_content)
        wiki_pages_created.append("wiki/identity.md")

        # 5b. wiki/domain/ pages
        domain_pages = synthesize_knowledge_pages(classified.domain, "domain", client)
        domain_dir = repo_path / "wiki" / "domain"
        for filename, content in domain_pages:
            page_path = domain_dir / filename
            page_path.write_text(content)
            wiki_pages_created.append(f"wiki/domain/{filename}")

        # 5c. wiki/techniques/ pages
        technique_pages = synthesize_knowledge_pages(
            classified.techniques, "techniques", client
        )
        techniques_dir = repo_path / "wiki" / "techniques"
        for filename, content in technique_pages:
            page_path = techniques_dir / filename
            page_path.write_text(content)
            wiki_pages_created.append(f"wiki/techniques/{filename}")

        # 5d. wiki/log.md — mechanical conversion of journal entries
        log_content = format_log_page(classified.log, created_date)
        log_page = repo_path / "wiki" / "log.md"
        log_page.write_text(log_content)
        wiki_pages_created.append("wiki/log.md")

    else:
        # anthropic not available — keep stub pages, warn, still migrate memories
        print(
            "Warning: anthropic package not available. "
            "Wiki stub pages will be kept as-is. Install 'anthropic' for full synthesis.",
            file=sys.stderr,
        )
        # Still write the log page mechanically (no LLM needed)
        log_content = format_log_page(classified.log, created_date)
        log_page = repo_path / "wiki" / "log.md"
        log_page.write_text(log_content)
        wiki_pages_created.append("wiki/log.md")

    # Step 6: Preserve legacy memories
    source_memories = source_dir / "memories"
    memories_preserved = 0
    if source_memories.exists():
        dest_memories = repo_path / "memories"
        shutil.copytree(str(source_memories), str(dest_memories), dirs_exist_ok=True)
        # Count .md files copied
        for tier_name in ("journal", "consolidated", "core"):
            tier_dir = dest_memories / tier_name
            if tier_dir.exists():
                memories_preserved += len(list(tier_dir.glob("*.md")))

    # Step 7: Migrate sessions → episodic
    sessions_dir = source_dir / "sessions"
    sessions_migrated = 0
    if sessions_dir.exists():
        episodic_dir = repo_path / "episodic"
        for jsonl_file in sessions_dir.glob("*.jsonl"):
            dest_file = episodic_dir / jsonl_file.name
            shutil.copy2(str(jsonl_file), str(dest_file))
            sessions_migrated += 1

    # Step 8: Commit migration result
    _run_git(repo_path, "add", "-A")
    _run_git(
        repo_path,
        "commit",
        "--allow-empty",
        "-m",
        f"Migration: {source_dir.name} \u2192 {new_name}",
    )

    return MigrationResult(
        entity_name=new_name,
        source_dir=source_dir,
        dest_dir=repo_path,
        wiki_pages_created=wiki_pages_created,
        memories_preserved=memories_preserved,
        sessions_migrated=sessions_migrated,
        unclassified_count=len(classified.unclassified),
    )
