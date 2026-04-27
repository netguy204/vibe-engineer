---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/entities.py
- src/templates/commands/entity-startup.md.jinja2
- src/templates/entity/wiki_schema.md.jinja2
code_references:
  - ref: src/entities.py#Entities::_wiki_schema_content
    implements: "Helper method that reads wiki/wiki_schema.md and returns its full text for embedding in the startup payload"
  - ref: src/entities.py#Entities::startup_payload
    implements: "Embeds full wiki schema content into the startup payload for wiki-based entities (replaces the brief inline bullet-list block)"
  - ref: src/templates/commands/entity-startup.md.jinja2
    implements: "Strengthened Step 6 wiki maintenance prompting with compounding artifact framing and concrete when→do triggers"
  - ref: src/templates/entity/wiki_schema.md.jinja2
    implements: "Enriched wiki schema document with compounding artifact framing and explicit Operations section (Ingest/Query/Lint)"
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

Wiki maintenance prompting in the entity startup payload is strong enough that entities actively maintain their wikis during work sessions. The full wiki schema document loads into the entity's initial context (not merely referenced for later reading), and the startup skill's maintenance section uses compounding-artifact framing with concrete when-X-do-Y triggers. The schema document and startup template reinforce each other — the schema is the reference, the startup makes it active — matching the effectiveness of the original LLM Wiki prompt.

### Context for implementing agent

**Read first**:
- `docs/investigations/entity_wiki_memory/OVERVIEW.md` — the broader investigation
- `docs/investigations/entity_wiki_memory/prototypes/llm_wiki_prompt.md` — the original LLM Wiki prompt whose effectiveness this chunk targets
- `src/templates/entity/wiki_schema.md.jinja2` — the wiki schema document
- `src/templates/commands/entity-startup.md.jinja2` — the startup skill template
- `src/entities.py` — `startup_payload()` assembles the startup context. `_wiki_schema_content()` reads the full schema for embedding alongside `_wiki_index_content()`.

**The problem this chunk addresses**:
1. A schema document referenced for later reading is not as effective as one loaded into the entity's initial context
2. Without in-session reinforcement of wiki maintenance, entities drift away from updating the wiki
3. Cross-references between wiki pages must be a primary maintenance target, not an afterthought
4. "Compounding artifact" framing makes wiki maintenance feel essential rather than optional

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
