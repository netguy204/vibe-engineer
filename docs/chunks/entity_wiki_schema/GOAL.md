---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/entity/wiki_schema.md.jinja2
- src/templates/entity/wiki/identity.md.jinja2
- src/templates/entity/wiki/index.md.jinja2
- src/templates/entity/wiki/log.md.jinja2
- src/entities.py
- tests/test_entities.py
code_references:
- ref: src/templates/entity/wiki_schema.md.jinja2
  implements: "Wiki schema instruction document — the CLAUDE.md for the wiki, describing directory structure, page conventions, maintenance workflow, Decision Rubric for routing findings to the correct wiki section, Operations (Ingest/Query/Lint), Identity.md Health Check, and Page Operations table"
- ref: src/templates/entity/wiki/identity.md.jinja2
  implements: "Initial identity page template for entity wiki (role, working style, values, hard-won lessons with routing guidance: principle-level entries that survive codebase changes, each ending with a See: link to mechanics pages)"
- ref: src/templates/entity/wiki/index.md.jinja2
  implements: "Initial index page template for entity wiki (content catalog with category tables and wikilinks)"
- ref: src/templates/entity/wiki/log.md.jinja2
  implements: "Initial log page template for entity wiki (chronological session log with format example)"
- ref: src/entities.py#Entities::create_entity
  implements: "Wiki directory initialization — creates wiki/ subdirectories and renders all four wiki templates during entity creation"
- ref: tests/test_entities.py#TestCreateEntityWiki
  implements: "Tests for wiki directory/page creation including structural and content correctness"
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

Define the canonical entity wiki schema — the structured, standardized knowledge base format that all entities use to maintain their personal knowledge during work sessions.

This is the foundational chunk: every other chunk in the entity wiki memory initiative depends on this schema definition. The schema serves as "the CLAUDE.md for the wiki" — the instructions that make an entity a disciplined wiki maintainer rather than a generic assistant.

The entity wiki replaces transcript-extracted journal entries with a persistent, compounding knowledge artifact. During sessions, entities maintain their wiki in real time as they learn, make decisions, and develop understanding. At shutdown, `git diff` of the wiki mechanically produces journal entries — no LLM extraction needed, no timeout pressure.

### Context for implementing agent

**Read the investigation first**: `docs/investigations/entity_wiki_memory/OVERVIEW.md` contains the full rationale, tested hypotheses, and architectural design for this initiative. Read it before implementing.

**The big picture**: Entities are evolving from ephemeral session workers into portable specialist employees that move across projects and teams via git submodules. Each entity gets its own git repo containing a wiki (structured knowledge base), memories (consolidated tiers), and episodic transcripts. The wiki is the primary knowledge store; the memory tiers become a fast-loading summary mechanism layered on top. At shutdown, `git diff` of the wiki mechanically produces journal entries, and Agent SDK consolidation synthesizes them into abstract memories. This eliminates the current fragile timeout-based journal extraction.

**Three prototype wikis** were built from real session transcripts and serve as golden-file references:
- `docs/investigations/entity_wiki_memory/prototypes/wiki_a/` — palette infrastructure entity (16 pages)
- `docs/investigations/entity_wiki_memory/prototypes/wiki_b/` — palette debugging entity (11 pages)
- `docs/investigations/entity_wiki_memory/prototypes/wiki_uniharness/` — architecture/design entity (15 pages)
- The schema prompt that produced them: `prototypes/wiki_schema.md`
- The LLM Wiki pattern document that inspired the design: `prototypes/llm_wiki_prompt.md`

Key findings from the investigation:
- The same schema produced coherent wikis across 3 very different entity types (infrastructure, debugging, architecture/design)
- All converged on: `index.md`, `identity.md`, `log.md`, `domain/`, `projects/`, `techniques/`, `relationships/`
- Most valuable wiki content came from failures and adversity — this is where memory matters most
- Wiki diffs from a second session produced 137 lines of structured journal-quality entries

**Entity templates** live at `src/templates/entity/`. The wiki templates sit alongside the base `identity.md.jinja2` template. The entity creation flow is in `src/entities.py` (`create_entity` function) and `src/cli/entity.py`.

**The LLM Wiki pattern** (full document at `prototypes/llm_wiki_prompt.md`): The wiki is a persistent, compounding artifact. The entity writes and maintains all of it — creating pages, updating them as new knowledge arrives, maintaining cross-references, flagging where new information contradicts old claims. The human/operator never writes the wiki. Key operations: **Ingest** (integrate new knowledge into existing pages), **Query** (search wiki to answer questions, file good answers back as pages), **Lint** (health-check for contradictions, stale claims, orphan pages, missing cross-references). Two special files: **index.md** (content catalog — the entity reads this first to find relevant pages) and **log.md** (chronological record of sessions and key events). The schema document is "the CLAUDE.md for the wiki" — it tells the entity how the wiki is structured, what conventions to follow, and what workflows to use when maintaining it.

### What to build

1. **Wiki schema template** (`src/templates/entity/wiki_schema.md.jinja2`): A Jinja2 template that renders into the entity's wiki directory as a schema document. This tells the entity:
   - The directory structure and what goes where
   - Page conventions (frontmatter format, wikilinks, page size limits)
   - What to capture during sessions (identity signals, domain knowledge, techniques, relationships, learnings)
   - How to maintain the wiki naturally as part of working (not as a separate "note-taking" step)
   - When to create new pages vs update existing ones
   - How to maintain the index and log

2. **Page templates**: Jinja2 templates for the initial wiki pages created when a new entity is initialized:
   - `wiki/identity.md` — skeleton with sections for role, working style, values, hard-won lessons
   - `wiki/index.md` — initial index with category tables
   - `wiki/log.md` — empty log with format example

3. **Schema registration**: Register the wiki schema in the entity initialization flow so `ve entity create` (chunk 1) can render it.

### Design constraints

- The schema must work for entities across all domains — infrastructure, design, research, debugging, architecture
- Page conventions must be simple enough that entities follow them naturally without explicit prompting every session
- The schema should encourage entities to maintain their wiki as a natural byproduct of working, not as a separate task
- Wikilinks (`[[page_name]]`) for cross-references — compatible with Obsidian for human browsing
- YAML frontmatter on every page with at minimum: `title`, `created`, `updated`

## Success Criteria

- Wiki schema template exists and renders correctly
- Page templates produce valid, well-structured initial wiki pages
- Schema document clearly instructs entities on wiki maintenance conventions
- Schema tested against the 3 prototype wikis — the conventions described should match what worked in the prototypes
- Templates registered in the entity template system for use by `ve entity create`
