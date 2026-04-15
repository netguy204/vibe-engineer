---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- src/entities.py
- src/templates/commands/entity-startup.md.jinja2
- tests/test_entities.py
code_references: []
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_wiki_schema
- entity_attach_detach
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Revise the entity-startup skill to load from the new wiki-based entity structure. At startup, the entity loads core memories for fast identity establishment, then the wiki index for structured knowledge overview, then recent consolidated memories. The entity's session instructions include the wiki schema so it knows to maintain its wiki during the session.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` — especially the "Runtime Wiki Maintenance" and "Startup Loading Order" sections in the Appendix.

**The big picture**: Entities are portable specialists whose knowledge lives in a wiki they maintain during every work session. The wiki is a structured, interlinked collection of markdown files (identity, domain knowledge, techniques, relationships, project notes, session log). The entity updates wiki pages in real time as it works — this is the entity's notebook, and taking notes is part of working, not a post-hoc extraction step. **This is the critical contract**: if the entity doesn't maintain its wiki during the session, the shutdown diff will be empty and no journal entries will be produced. Getting the wiki schema instructions into the session context correctly is what makes the entire pipeline work.

**Existing startup code**:
- `src/entities.py` — `startup_payload(name)` generates the full startup context. Currently loads identity file, core memories, consolidated memory index, and touch protocol instructions. This is what needs to be revised.
- `src/templates/commands/entity-startup.md.jinja2` — the `/entity-startup` skill template. 8-step process: identity adoption, core memory internalization, consolidated index, touch protocol, episodic search, active state restoration. This needs to be updated to include wiki loading and schema injection.
- `src/models/entity.py` — `MemoryTier` enum (JOURNAL, CONSOLIDATED, CORE), `MemoryFrontmatter` model, `EntityIdentity` model.

**The LLM Wiki pattern** (full doc at `docs/investigations/entity_wiki_memory/prototypes/llm_wiki_prompt.md`): The wiki has three layers — raw sources (immutable), the wiki itself (entity-maintained), and the schema (conventions document). The schema tells the entity how to maintain its wiki: when to create new pages, how to update existing ones, how to maintain cross-references, when to lint for contradictions. Two key files: **index.md** (content catalog the entity reads first to orient) and **log.md** (chronological session record). The entity reads the index to find relevant pages, drills into them as needed, and files new knowledge back into the wiki as it works.

**Startup loading order** (from investigation):
1. Core memories (fast identity establishment — who I am, what I value)
2. Wiki `index.md` (structured knowledge overview — what I know)
3. Recent consolidated memories (cross-session patterns)
4. Deep wiki pages loaded on-demand during session (not at startup)

**Critical design point**: The wiki schema instructions must be included in the entity's session context (e.g., appended to CLAUDE.md or injected as a system prompt) so the entity knows to maintain its wiki as a natural byproduct of working. The entity should update wiki pages in real time as it learns — this is not a separate "take notes" step.

### What to build

1. **Revised startup payload**: Update the entity startup skill to:
   - Detect whether the entity has a wiki/ directory (new format) or just memories/ (legacy)
   - For wiki entities: load core memories → wiki/index.md → recent consolidated memories
   - For legacy entities: preserve current behavior
   - Include wiki schema instructions in the session context

2. **Wiki schema injection**: The wiki maintenance instructions need to be part of the entity's working context. Options:
   - Append to the project's CLAUDE.md during entity start
   - Include in the entity-startup skill output
   - Render into a file the entity reads at startup
   Choose the approach that's most natural for the entity to follow without explicit reminding.

3. **On-demand wiki reading**: The entity should be able to `grep` or read specific wiki pages during the session when it needs detailed knowledge. The startup payload doesn't load everything — just enough to establish identity and orient.

### Design constraints

- Must be backward-compatible with legacy entities (no wiki/ directory)
- Core memories + wiki index should fit comfortably in the initial context (target: under 5K tokens for startup payload)
- The entity should feel natural maintaining its wiki — the schema instructions should be clear but not overwhelming
- Don't load the entire wiki at startup — just index.md for orientation

## Success Criteria

- Entity startup with a wiki-based entity loads core memories, wiki index, and consolidated memories in the correct order
- Entity startup with a legacy entity preserves current behavior
- Wiki schema instructions are available to the entity during the session
- The entity can read specific wiki pages on-demand during work
- Startup payload stays under 5K tokens for a typical entity
- Tests cover both wiki and legacy entity paths
