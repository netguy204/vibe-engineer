

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Entities are a new top-level concept in VE. Unlike workflow artifacts (chunks, narratives, investigations, subsystems) which live under `docs/` and follow the `ArtifactManager` pattern, entities live under `.entities/` at the project root and represent long-running agent personas with tiered memories.

**Why not ArtifactManager?** Entities are not workflow documentation artifacts — they are runtime state for agent personas. They don't have frontmatter-driven lifecycle status, they don't live under `docs/`, and their "main file" (`identity.md`) serves a fundamentally different purpose than chunk GOAL.md or investigation OVERVIEW.md. The ArtifactManager pattern (DEC-009) is wrong here. Instead, we build a standalone `Entities` class and `EntityMemory` model that follow the project's conventions (Pydantic models per DEC-008, Click CLI groups per DEC-001) without forcing the artifact lifecycle pattern.

**Memory file format: Markdown with YAML frontmatter.** Each memory is a single `.md` file with structured frontmatter (title, category, valence, salience, tier, last_reinforced, recurrence_count) and free-text content. This matches the project's documentation-centric philosophy and makes memories human-readable. The prototype used JSON arrays, but individual files per memory enable simpler reinforcement updates (touch a single file's `last_reinforced` timestamp without rewriting an array) and easier human inspection.

**Directory structure** follows the investigation's design:
```
.entities/
  <name>/
    identity.md         # Entity role, startup instructions
    memories/
      journal/          # Tier 0: raw session memories
      consolidated/     # Tier 1: cross-session patterns
      core/             # Tier 2: persistent skills
```

**Testing strategy:** TDD per TESTING_PHILOSOPHY.md. The domain logic (Entities class, memory models, directory creation) is tested at unit level. The CLI commands (`ve entity create`, `ve entity list`) are tested as CLI integration tests using Click's CliRunner. Tests focus on semantic assertions: directories exist with correct structure, memory files parse correctly, prototype memories round-trip without loss.

## Subsystem Considerations

- **docs/subsystems/template_system** (DOCUMENTED): This chunk USES the template system to render `identity.md` from a Jinja2 template when creating entities. We follow the existing pattern: template in `src/templates/`, rendered via `render_to_directory()`.
- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk does NOT use the workflow_artifacts subsystem. Entities are not workflow artifacts — they have no lifecycle status transitions and do not follow the ArtifactManager pattern. This is a deliberate deviation from the subsystem's scope, not a failure to follow its patterns.

## Sequence

### Step 1: Define Pydantic models for memory and entity identity

Create `src/models/entity.py` with:

- `MemoryTier(StrEnum)` — `JOURNAL = "journal"`, `CONSOLIDATED = "consolidated"`, `CORE = "core"`
- `MemoryCategory(StrEnum)` — `CORRECTION`, `SKILL`, `DOMAIN`, `CONFIRMATION`, `COORDINATION`, `AUTONOMY` (from the investigation's taxonomy)
- `MemoryValence(StrEnum)` — `POSITIVE`, `NEGATIVE`, `NEUTRAL`
- `MemoryFrontmatter(BaseModel)`:
  - `title: str` — short title (3-8 words)
  - `category: MemoryCategory`
  - `valence: MemoryValence`
  - `salience: int` — 1-5, validated with `Field(ge=1, le=5)`
  - `tier: MemoryTier`
  - `last_reinforced: datetime` — ISO 8601 timestamp
  - `recurrence_count: int` — how many times this pattern was observed, `Field(ge=0)`
  - `source_memories: list[str]` — titles of memories this was consolidated from (empty for tier 0)
- `EntityIdentity(BaseModel)`:
  - `name: str` — entity name (validated: lowercase, alphanumeric + underscores)
  - `role: str | None = None` — brief description of entity's purpose
  - `created: datetime`

Add re-exports in `src/models/__init__.py`.

Write **failing tests first** in `tests/test_entity_models.py`:
- `MemoryFrontmatter` rejects salience outside 1-5
- `MemoryFrontmatter` rejects invalid tier/category/valence values
- `EntityIdentity` rejects names with spaces or special characters
- Round-trip: prototype memory data (from investigation) parses into `MemoryFrontmatter` without loss

Location: `src/models/entity.py`, `tests/test_entity_models.py`

### Step 2: Define the Entities domain class

Create `src/entities.py` with an `Entities` class:

- `__init__(self, project_dir: Path)` — stores project root
- `entities_dir` property → `project_dir / ".entities"`
- `entity_dir(name: str) -> Path` → `entities_dir / name`
- `list_entities() -> list[str]` → enumerate subdirectory names under `.entities/`
- `entity_exists(name: str) -> bool`
- `create_entity(name: str, role: str | None = None) -> Path`:
  - Validates name (lowercase alphanumeric + underscores)
  - Creates directory structure:
    ```
    .entities/<name>/
      identity.md
      memories/
        journal/
        consolidated/
        core/
    ```
  - Renders `identity.md` from a template with name, role, created timestamp
  - Returns path to entity directory
  - Raises `ValueError` if entity already exists
- `parse_identity(name: str) -> EntityIdentity | None` — parse identity.md frontmatter
- `list_memories(name: str, tier: MemoryTier | None = None) -> list[MemoryFrontmatter]` — enumerate memory files, optionally filtered by tier
- `get_memory_path(name: str, tier: MemoryTier, memory_id: str) -> Path`
- `memory_index(name: str) -> dict` — build startup index: all core memories (full), consolidated titles only

Write **failing tests first** in `tests/test_entities.py`:
- `create_entity` creates correct directory structure
- `create_entity` raises on duplicate name
- `create_entity` raises on invalid name (spaces, uppercase, special chars)
- `list_entities` returns empty list when no entities
- `list_entities` returns entity names after creation
- `list_memories` returns memories filtered by tier
- `memory_index` returns core memories in full, consolidated as titles-only

Location: `src/entities.py`, `tests/test_entities.py`

### Step 3: Create identity.md template

Create `src/templates/entity/identity.md.jinja2`:

```markdown
---
name: {{ name }}
role: {{ role or "" }}
created: {{ created }}
---

# {{ name }}

{{ role or "This entity has not yet been given a role description." }}

## Startup Instructions

<!-- Add instructions that should be loaded when this entity wakes up. -->
```

This follows the template system pattern: templates in `src/templates/`, rendered to the target directory.

Location: `src/templates/entity/identity.md.jinja2`

### Step 4: Define the memory file format and write/parse helpers

Add to `src/entities.py` (or a separate `src/entity_memory.py` if size warrants):

- `write_memory(entity_name: str, memory: MemoryFrontmatter, content: str) -> Path`:
  - Generates a filename: `{timestamp}_{slugified_title}.md` (timestamp ensures uniqueness)
  - Writes markdown file with YAML frontmatter (from `MemoryFrontmatter.model_dump()`) and content body
  - Writes to the appropriate tier subdirectory
  - Returns path to the created file
- `parse_memory(file_path: Path) -> tuple[MemoryFrontmatter, str]`:
  - Reads a memory file, parses frontmatter with Pydantic, returns (frontmatter, content)
- `update_memory_field(file_path: Path, field: str, value: Any)`:
  - Update a single frontmatter field (reuses `frontmatter.update_frontmatter_field`)

Write **failing tests first** in `tests/test_entities.py` (or `tests/test_entity_memory.py`):
- `write_memory` creates file in correct tier directory
- `parse_memory` round-trips: write then parse returns same data
- Prototype memories from investigation parse correctly (test with actual example data from consolidate.py's output format, adapted to our frontmatter schema)
- `update_memory_field` modifies `last_reinforced` without corrupting other fields

Location: `src/entities.py`, `tests/test_entities.py`

### Step 5: Implement `ve entity create` CLI command

Create `src/cli/entity.py` with a Click command group:

```python
@click.group()
def entity():
    """Manage entities - long-running agent personas with persistent memory."""
    pass

@entity.command("create")
@click.argument("name")
@click.option("--role", default=None, help="Brief description of entity's purpose")
@click.option("--project-dir", type=click.Path(...), default=".")
def create(name, role, project_dir):
    ...
```

Register in `src/cli/__init__.py`: import and `cli.add_command(entity)`.

Write **failing tests first** in `tests/test_entity_cli.py`:
- `ve entity create mysteward` creates `.entities/mysteward/` with correct structure
- `ve entity create mysteward` twice → error on second invocation
- `ve entity create "bad name"` → validation error
- Exit code 0 on success, non-zero on error
- Output includes entity name and path

Location: `src/cli/entity.py`, `src/cli/__init__.py`, `tests/test_entity_cli.py`

### Step 6: Implement `ve entity list` CLI command

Add to `src/cli/entity.py`:

```python
@entity.command("list")
@click.option("--project-dir", type=click.Path(...), default=".")
def list_entities(project_dir):
    ...
```

Write **failing tests first** in `tests/test_entity_cli.py`:
- `ve entity list` with no entities → empty output (or "No entities found")
- `ve entity list` after creating entities → lists them
- Output includes entity names

Location: `src/cli/entity.py`, `tests/test_entity_cli.py`

### Step 7: Validate prototype memory round-trip

Create a test that takes representative data from the investigation prototypes and verifies it stores in the new schema without loss. Specifically:

- Take example tier-2 core memory objects from the consolidation prototype's output format:
  ```json
  {
    "title": "Verify state before acting",
    "content": "Always check the current state of a resource before taking action...",
    "valence": "negative",
    "category": "correction",
    "salience": 5,
    "tier": 2,
    "source_memories": ["Check PR state before acting", "..."],
    "recurrence_count": 5
  }
  ```
- Convert to `MemoryFrontmatter` + content string
- Write as a memory file
- Parse back and verify all fields match
- Repeat for tier-1 consolidated and tier-0 journal examples

This test validates the success criterion: "Prototype tier-2 memories from the investigation can be stored in the new schema without loss."

Location: `tests/test_entities.py`

### Step 8: Update GOAL.md code_paths

Update the chunk's `code_paths` frontmatter to list all files created or modified.

Backreference comments should be added to:
- `src/entities.py` (module-level): `# Chunk: docs/chunks/entity_memory_schema`
- `src/models/entity.py` (module-level): `# Chunk: docs/chunks/entity_memory_schema`
- `src/cli/entity.py` (module-level): `# Chunk: docs/chunks/entity_memory_schema`

## Dependencies

No chunk dependencies. This is the foundation chunk for the entity memory system — all other entity chunks (shutdown_skill, startup_skill, touch_command, memory_decay) depend on this one.

Existing infrastructure used:
- `src/frontmatter.py` — reuse `parse_frontmatter()` and `update_frontmatter_field()` for memory files
- `src/templates/` + `src/template_system.py` — render `identity.md` template
- `src/models/` — Pydantic model patterns (DEC-008)
- `src/cli/__init__.py` — CLI registration (DEC-001)

## Risks and Open Questions

- **Memory filename collisions**: Using `{timestamp}_{slug}.md` should be unique, but if two memories are written in the same second with similar titles, collisions could occur. Mitigation: include a short random suffix or use microsecond precision.
- **Frontmatter parser reuse**: The existing `frontmatter.py` module uses `parse_frontmatter(path, model_class)` which expects the VE frontmatter convention (YAML between `---` delimiters). Memory files will use the same convention, so this should work. Verify that `update_frontmatter_field` handles datetime serialization correctly.
- **`.entities/` in `.gitignore`?**: Entity memories are likely entity-private runtime state. Whether they should be committed to version control is a user decision. This chunk does NOT prescribe gitignore behavior — that's an entity harness concern. But we should document the consideration.
- **Template rendering for identity.md**: The template system uses `render_to_directory()` which renders all templates in a source dir to a target dir. For entity creation, we may need a more targeted approach — render a single template file. Check if the template system supports this or if we need a simpler direct Jinja2 render.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->