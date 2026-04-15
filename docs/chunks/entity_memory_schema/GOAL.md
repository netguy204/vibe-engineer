---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models/entity.py
  - src/models/__init__.py
  - src/entities.py
  - src/cli/entity.py
  - src/cli/__init__.py
  - src/templates/entity/identity.md.jinja2
  - tests/test_entity_models.py
  - tests/test_entities.py
  - tests/test_entity_cli.py
code_references:
  - ref: src/models/entity.py#MemoryTier
    implements: "Three-tier memory hierarchy enum (journal, consolidated, core)"
  - ref: src/models/entity.py#MemoryCategory
    implements: "Memory category taxonomy from agent memory investigation"
  - ref: src/models/entity.py#MemoryValence
    implements: "Emotional valence classification for memories"
  - ref: src/models/entity.py#MemoryFrontmatter
    implements: "Frontmatter schema for memory files with all required fields (salience, tier, last_reinforced, recurrence_count, source_memories)"
  - ref: src/models/entity.py#EntityIdentity
    implements: "Entity identity model with name validation"
  - ref: src/entities.py#Entities
    implements: "Entity lifecycle management: create, list, parse identity, memory CRUD, and startup memory index"
  - ref: src/entities.py#Entities::create_entity
    implements: "Directory structure creation (.entities/<name>/ with identity.md, memory tier subdirectories, and wiki/ directory with subdirectories and initial pages)"
  - ref: src/entities.py#Entities::write_memory
    implements: "Memory file writing with YAML frontmatter and unique filename generation"
  - ref: src/entities.py#Entities::parse_memory
    implements: "Memory file parsing (frontmatter + content extraction)"
  - ref: src/entities.py#Entities::memory_index
    implements: "Startup memory index: core memories in full, consolidated as titles-only"
  - ref: src/entities.py#Entities::update_memory_field
    implements: "Single-field frontmatter update for memory files (e.g., last_reinforced)"
  - ref: src/cli/entity.py#create
    implements: "ve entity create CLI command"
  - ref: src/cli/entity.py#list_entities
    implements: "ve entity list CLI command"
  - ref: src/templates/entity/identity.md.jinja2
    implements: "Jinja2 template for entity identity.md rendering"
narrative: null
investigation: agent_memory_consolidation
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after: []
---

# Chunk Goal

## Minor Goal

Define the on-disk directory structure and file formats for entities and their tiered memories. An entity is a named, long-running agent persona (e.g., a steward) that accumulates understanding across sessions. This chunk establishes the storage foundation all other entity memory chunks depend on.

The structure must support:
- Multiple entities per working directory (`.entities/<name>/`)
- Three memory tiers: journal (tier 0), consolidated (tier 1), core (tier 2)
- Memory files with metadata: title, content, category, valence, salience, `last_reinforced` timestamp, tier, recurrence count
- An entity identity file (`identity.md`) describing the entity's role and startup instructions
- A memory index for the startup skill to read

## Success Criteria

- `.entities/<name>/` directory structure is defined and documented
- Memory file format (JSON or markdown with frontmatter) is specified with all required fields
- `ve entity create <name>` command creates the directory structure and a template `identity.md`
- `ve entity list` shows entities in the current project
- The schema supports the decay mechanics: `last_reinforced` timestamp, tier field, capacity budgets
- Prototype tier-2 memories from the investigation (`docs/investigations/agent_memory_consolidation/prototypes/tiers/`) can be stored in the new schema without loss

## Rejected Ideas

### Session-scoped storage

Memories scoped to session IDs rather than entity names. Rejected because entities persist across many sessions — their memories are their identity, not artifacts of a single conversation.

### Continuous journaling as a separate tier

A fourth tier for real-time micro-memories recorded during interaction. Deferred because the investigation showed post-hoc shutdown extraction from the full session transcript is sufficient.