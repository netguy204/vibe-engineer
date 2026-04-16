---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- src/entities.py
- src/templates/commands/entity-startup.md.jinja2
- src/templates/entity/wiki_schema.md.jinja2
code_references: []
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Strengthen wiki maintenance prompting in the entity startup payload so entities actually maintain their wikis during work sessions. Currently entities are told to maintain their wiki in step 6 of the startup skill, but the schema document is not loaded into context and the maintenance instruction is brief and easy to forget. Real-world observation: entities are not maintaining their wikis effectively, and cross-references are weaker than what the original LLM Wiki prompt produced.

### Context for implementing agent

**Read first**:
- `docs/investigations/entity_wiki_memory/OVERVIEW.md` — the broader investigation
- `docs/investigations/entity_wiki_memory/prototypes/llm_wiki_prompt.md` — the original LLM Wiki prompt that this chunk is trying to match the effectiveness of
- `src/templates/entity/wiki_schema.md.jinja2` — the current wiki schema document (already good content; just not loaded effectively)
- `src/templates/commands/entity-startup.md.jinja2` — the startup skill template that needs strengthening
- `src/entities.py` — `startup_payload()` is the function that assembles the startup context. `_wiki_index_content()` currently loads only the index. This chunk extends it to load the full schema.

**The problem observed**:
1. Entities are told to maintain wiki at startup step 6, but the schema document (`wiki/wiki_schema.md`) is referenced but not loaded into context
2. Once the session is underway, there is no reinforcement of wiki maintenance — entities forget
3. Cross-references between wiki pages are weaker than what the original LLM Wiki prompt produced
4. The "compounding artifact" framing that motivates the original prompt is missing — without it, wiki maintenance feels optional rather than essential

**The constraint**:
- **Do NOT modify CLAUDE.md / AGENTS.md** — those files are read by tools other than entities. Entity-specific instruction must live in the startup payload only.

### What to build

1. **Load the full wiki schema into the startup payload**: In `src/entities.py`, extend `startup_payload()` so that for wiki-based entities, the full content of `wiki/wiki_schema.md` is included in the payload. The entity should see the schema in its initial context, not just be told to read it later.

2. **Strengthen maintenance prompting in the startup skill template**: Update `src/templates/commands/entity-startup.md.jinja2` step 6 to be more emphatic and concrete. Borrow patterns from the original LLM Wiki prompt:
   - Frame the wiki as a **persistent, compounding artifact** (contrast with rediscovering knowledge each session)
   - State that **the cross-references are the value** — connections between pages compound over time
   - Make the maintenance triggers concrete and active (when X happens, do Y)
   - Emphasize that **most valuable content comes from adversity** (failures, surprises, corrections)
   - Reframe wiki maintenance as part of working, not separate from it

3. **Strengthen the wiki schema document**: Review `src/templates/entity/wiki_schema.md.jinja2` and incorporate the strongest patterns from the LLM Wiki prompt:
   - The "compounding artifact" framing in the schema itself
   - Explicit operations: Ingest (integrate new knowledge), Query (search wiki, file good answers back), Lint (health-check for contradictions, stale claims, orphan pages, missing cross-references)
   - Stronger emphasis on cross-reference maintenance — the connections between pages are the value, not just the pages themselves
   - When working through a problem, the entity should ingest the experience back into the wiki (file good answers as new pages, update existing pages with new examples)

4. **Test against expected behavior**: After this chunk lands, an entity should:
   - Reference the wiki schema in its first response when asked about its workflow
   - Naturally update wiki pages as it works (not just at session end)
   - Create wikilinks between related pages without being prompted
   - Lint its own wiki periodically (notice when a new concept lacks a page, when a page references a concept that doesn't have its own page, etc.)

### Design constraints

- Do NOT modify CLAUDE.md / AGENTS.md — entity-specific instruction lives only in the startup payload
- Schema document and startup template should reinforce each other — the schema is reference, the startup makes it active
- Keep the startup payload reasonable size — full schema is ~150 lines, this is fine
- Backward compatible with legacy entities (no wiki/) — only changes the wiki-aware code path

## Success Criteria

- `wiki/wiki_schema.md` content is included in the startup payload for wiki-based entities
- Startup skill template's wiki maintenance section is substantially expanded with the patterns above
- Wiki schema document incorporates the "compounding artifact" framing and explicit operations
- After landing, entities visibly maintain wikis during sessions (operator verification)
- No changes to CLAUDE.md / AGENTS.md
- Tests cover: payload includes schema for wiki entities, payload omits schema for legacy entities
