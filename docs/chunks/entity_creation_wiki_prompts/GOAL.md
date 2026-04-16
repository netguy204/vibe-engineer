---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- src/entity_from_transcript.py
- src/entity_migration.py
code_references: []
narrative: null
investigation: entity_wiki_memory
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_wiki_maintenance_prompt
created_after:
- board_watch_reconnect_fix
---
# Chunk Goal

## Minor Goal

Strengthen the wiki construction prompts used by entity creation paths (`from-transcript`, `ingest-transcript`, and `migrate`) so they produce wikis with richer cross-references and better adherence to the LLM Wiki pattern. Sibling to `entity_wiki_maintenance_prompt`, which improves runtime wiki maintenance — this chunk improves initial construction.

### Context for implementing agent

**Read first**:
- `docs/investigations/entity_wiki_memory/OVERVIEW.md` — the broader investigation
- `docs/investigations/entity_wiki_memory/prototypes/llm_wiki_prompt.md` — the original LLM Wiki prompt whose quality we want to match
- `docs/chunks/entity_wiki_maintenance_prompt/GOAL.md` — sibling chunk that strengthens startup prompting and schema document. This chunk extends those improvements to creation paths.

**The problem observed**: Real entities maintained by the current system have weaker cross-references than what the original LLM Wiki prompt produced. The `entity_wiki_maintenance_prompt` chunk addresses the startup / runtime side (entities actively maintain their wikis during sessions). This chunk addresses the creation side — the initial wiki should start with the same quality bar, with rich interlinking and coherent structure.

**Existing prompts to strengthen**:
- `src/entity_from_transcript.py:_wiki_creation_prompt` — first-transcript wiki construction
- `src/entity_from_transcript.py:_wiki_update_prompt` — subsequent-transcript incremental wiki update
- `src/entity_migration.py:synthesize_identity_page` — legacy memory → identity.md synthesis
- `src/entity_migration.py:synthesize_knowledge_pages` — legacy memory → domain/techniques page synthesis

All of these should reflect the improvements to `wiki/wiki_schema.md` made by `entity_wiki_maintenance_prompt`. The schema document is already referenced in the creation prompt but the prompt itself can be stronger.

### What to build

1. **Strengthen `_wiki_creation_prompt`** (from-transcript first pass):
   - Frame the wiki as a **compounding knowledge artifact** where cross-references ARE the value (not just decoration)
   - Explicit lint operation as part of construction: after writing pages, do a pass to check for missing cross-references, concepts mentioned but lacking their own page, potential contradictions
   - Emphasize that **most valuable content comes from adversity** in the transcript — failures, surprises, corrections
   - Borrow the Ingest operation framing: "you are not just summarizing the transcript, you are integrating its knowledge into a structured wiki"

2. **Strengthen `_wiki_update_prompt`** (from-transcript / ingest-transcript subsequent passes):
   - Emphasize that subsequent transcripts are **compounding** onto existing knowledge — revise pages where new evidence deepens understanding, add cross-references between old and new pages, note contradictions when new data conflicts with old claims
   - Explicit lint operation: check whether any new concept from the transcript needs a page, whether any existing page needs updates in light of new context, whether cross-references between new and existing pages are in place
   - Preserve the entity's identity evolution — if the entity's self-model changed during the session, capture that in identity.md

3. **Strengthen migration synthesis prompts** (migrate):
   - `synthesize_identity_page`: produce identity content with the same structure and depth as the original LLM Wiki prompt produces, not just a summary of core memories
   - `synthesize_knowledge_pages`: group legacy memories into coherent domain/technique pages with cross-references, not isolated page dumps
   - Add a post-synthesis lint pass: after generating all pages, review and add cross-references between related pages

4. **Post-creation lint step** (optional but valuable):
   - After the wiki is constructed, run a lint pass that specifically audits cross-reference density and orphan pages
   - Report what was added/fixed as part of the creation summary

### Design constraints

- Reuse improved wiki schema document — do not duplicate schema content in prompts
- Maintain the existing creation interfaces — no new required flags
- Quality bar: resulting wikis should have cross-reference density comparable to the investigation prototypes (`docs/investigations/entity_wiki_memory/prototypes/wiki_a/`, `wiki_b/`, `wiki_uniharness/`)

## Success Criteria

- Creation prompts include the compounding-artifact framing and explicit lint operations
- Migration synthesis prompts produce wikis with strong cross-references (not isolated pages)
- After landing, new entities (via from-transcript, ingest-transcript, migrate) have cross-reference density comparable to the investigation prototypes
- Tests cover: creation prompts include lint guidance, migration prompts reference cross-reference requirements
