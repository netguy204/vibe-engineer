---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- src/entity_migration.py
- tests/test_entity_migration.py
- tests/test_entity_migrate_cli.py
code_references:
- ref: src/entity_migration.py#LegacyMemory
  implements: "Data model for a single legacy memory file"
- ref: src/entity_migration.py#ClassifiedMemories
  implements: "Grouped memory buckets (identity/domain/techniques/relationships/log/unclassified)"
- ref: src/entity_migration.py#MigrationResult
  implements: "Migration summary returned to caller and printed by CLI"
- ref: src/entity_migration.py#read_legacy_entity
  implements: "Reads legacy .entities/<name>/ structure into structured data"
- ref: src/entity_migration.py#classify_memories
  implements: "Routes each LegacyMemory into the appropriate wiki bucket"
- ref: src/entity_migration.py#format_log_page
  implements: "Mechanically converts journal-tier memories to wiki/log.md (no LLM)"
- ref: src/entity_migration.py#synthesize_identity_page
  implements: "LLM synthesis of core/correction/autonomy memories into wiki/identity.md"
- ref: src/entity_migration.py#synthesize_knowledge_pages
  implements: "LLM grouping of domain/skill memories into focused wiki pages"
- ref: src/entity_migration.py#migrate_entity
  implements: "Full migration orchestration: read → classify → create repo → synthesize wiki → copy memories → commit"
- ref: src/cli/entity.py#migrate
  implements: "ve entity migrate CLI command: resolves paths, calls migrate_entity, prints summary"
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_wiki_schema
- entity_repo_structure
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Create a migration tool that converts existing entities (current journal/consolidated/core memory format in `.entities/`) to the new wiki-based git repo structure. This is critical for preserving the valuable specialist knowledge that existing entities have accumulated.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the H4 exploration log showing how wikis were constructed from session data, and the prototype wikis that serve as quality references.

**The big picture**: The operator has trained valuable specialist entities using the current memory system. These specialists have real expertise — domain knowledge, working patterns, calibrated judgment — accumulated over many sessions. This migration tool preserves that investment by converting existing entities to the new wiki-based format so they can benefit from the wiki, git portability, and improved consolidation pipeline.

**Existing entity structure** (what you're migrating FROM):
```
.entities/<uuid>/
├── identity.md                    # YAML frontmatter with name, role
├── memories/
│   ├── journal/*.md               # Session-level memories (frontmatter: title, category, valence, salience, tier)
│   ├── consolidated/*.md          # Cross-session patterns
│   └── core/*.md                  # Identity-level memories
└── sessions/*.jsonl               # Archived session transcripts (episodic)
```

**Key code to understand**:
- `src/entities.py` — `startup_payload()` shows how existing memories are loaded and formatted. `_build_tier_payload()` reads memory files and formats them. Memory files have YAML frontmatter with fields defined in `src/models/entity.py`: `MemoryFrontmatter` (title, content, category, valence, salience 1-5, tier, last_reinforced, recurrence_count, source_memories).
- `src/models/entity.py` — `MemoryCategory` enum: correction, skill, domain, confirmation, coordination, autonomy. These categories map naturally to wiki sections: domain → `wiki/domain/`, skill → `wiki/techniques/`, correction → `wiki/identity.md` (hard-won lessons).
- Entity names currently use UUIDs (e.g., `58d36632-bf65-4ba3-8f34-481cf64e9701`). Migration should ask for a human-readable name.

**Prototype wikis as quality references**: The 3 prototype wikis at `docs/investigations/entity_wiki_memory/prototypes/wiki_a/`, `wiki_b/`, `wiki_uniharness/` show what good migration output looks like. The migration's LLM synthesis should produce wiki pages of similar quality — structured, cross-referenced, with clear identity/domain/technique separation.

**The LLM Wiki pattern** guides the migration output format: each wiki page should be focused (one concept per page), use wikilinks for cross-references, have YAML frontmatter, and be organized into the standard directories (domain/, projects/, techniques/, relationships/). The index.md should catalog all pages with one-line summaries. The identity.md should capture role, working style, values, and hard-won lessons — not just dump core memory text.

Existing entities have knowledge stored as:
- `.entities/<uuid>/memories/journal/*.md` — session-level memories
- `.entities/<uuid>/memories/consolidated/*.md` — cross-session patterns
- `.entities/<uuid>/memories/core/*.md` — identity-level memories
- `.entities/<uuid>/identity.md` — entity identity file
- Episodic transcripts in `~/.claude/projects/` directories

The investigation's H4 prototype demonstrated that wikis can be constructed from session transcripts — the same approach works for migration: read existing memories and construct an initial wiki that captures the entity's accumulated knowledge in the new structured format.

### What to build

1. **`ve entity migrate <name> [--entity-dir <path>]`**: CLI command that:
   - Locates the existing entity at `.entities/<name>/` (or specified path)
   - Reads all existing memories (journal, consolidated, core)
   - Reads the entity's identity file
   - Creates a new entity repo structure (using `entity_repo_structure` module)
   - Populates the wiki from existing memories:
     - `wiki/identity.md` ← core memories + identity file (who I am, values, lessons)
     - `wiki/domain/` pages ← consolidated memories grouped by topic
     - `wiki/techniques/` pages ← consolidated memories about approaches/patterns
     - `wiki/relationships/` pages ← any relationship information from memories
     - `wiki/log.md` ← journal entries converted to chronological log
     - `wiki/index.md` ← generated from all created pages
   - Preserves original memories in `memories/` (the wiki is additive, not a replacement)
   - Initializes git repo and makes initial commit
   - Prints migration summary: pages created, knowledge preserved, any gaps

2. **Memory-to-wiki transformer** (`entity_migration.py`):
   - `read_legacy_memories(entity_dir)` → structured memory collection
   - `classify_memories(memories)` → group into wiki categories (identity, domain, techniques, relationships)
   - `generate_wiki_pages(classified)` → render wiki pages from memory groups
   - Uses LLM (via Agent SDK) to synthesize memories into coherent wiki pages — this is a one-time migration cost that produces a much richer starting point than the raw memories alone

3. **Migration validation**:
   - After migration, verify that key information from core memories appears in wiki/identity.md
   - Verify that consolidated memory topics map to domain/technique pages
   - Report any memories that couldn't be classified (flagged for manual review)

### Design constraints

- **Non-destructive**: Keep original `.entities/<name>/` intact until migration is verified. The new repo is created alongside, not in-place.
- **LLM-assisted**: Use the Agent SDK to synthesize memories into wiki pages — don't just dump raw memory text into wiki files. The LLM should organize, cross-reference, and structure the content.
- **One-time cost**: Migration runs once per entity. It's acceptable for this to take a few minutes and cost some API usage.
- **Preserve existing name**: Existing entities already have human-readable names (e.g., `steward`, `creator`, `palette`). The migration should use the existing directory name as the entity repo name.
- **Preserve episodic**: If episodic transcripts exist, copy them into the new structure's `episodic/` directory.

## Success Criteria

- `ve entity migrate palette` creates a wiki-based entity repo from the existing `.entities/palette/` directory
- Wiki pages are coherent and well-structured (not raw memory dumps)
- Core memories map to identity.md values/lessons
- Consolidated memories map to domain and technique pages
- Journal entries map to log.md entries
- Original memories preserved in memories/ directory
- Migration summary reports what was created and any gaps
- Tests cover: full migration, empty entity, entity with only core memories
