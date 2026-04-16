

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Three files change; all changes are self-contained with no new dependencies:

1. **`src/entities.py`** — add `_wiki_schema_content()` helper (mirrors the existing `_wiki_index_content()` pattern), call it inside `startup_payload()` to embed the full schema text directly into the wiki section of the context payload. This eliminates the "go read this file later" gap for wiki entities.

2. **`src/templates/commands/entity-startup.md.jinja2`** — strengthen Step 6. The current step is brief and easy to skim past. Expand it to borrow the motivational framing from the LLM Wiki prompt: compounding artifact, cross-references as the primary value, concrete triggers, adversity as the richest source. The goal is that an entity reading Step 6 internalizes the *why*, not just the mechanics.

3. **`src/templates/entity/wiki_schema.md.jinja2`** — enrich the schema document itself. The content is already good; it needs the compounding artifact framing at the top, and an explicit **Operations** section (Ingest / Query / Lint) borrowed from the LLM Wiki prompt. These operations give the entity a concrete vocabulary for self-directed wiki work rather than just reactive updates.

Both template changes are pure prose edits — no new template variables, no rendering logic changes.

Following the project's TDD practice, tests for the `startup_payload()` changes are written first (Step 1) before the implementation (Step 2).

## Sequence

### Step 1: Write failing tests for `startup_payload()` schema inclusion

Add tests to `tests/test_entities.py` (in a new `TestStartupPayloadWikiSchema` class) that cover the two success criteria:

- **Wiki entity**: Call `startup_payload()` on an entity that has a `wiki/` directory. Assert that the returned payload contains a key phrase from `wiki/wiki_schema.md` — specifically, something that would only appear if the schema file content was loaded (e.g. the heading `# Wiki Schema` or the phrase `compounding artifact`). Use `entities.create_entity()` to set up the fixture; `create_entity()` already writes `wiki/wiki_schema.md` from the template.

- **Legacy entity**: Call `startup_payload()` on an entity created without `wiki/` (manually remove the wiki dir after creation, or write a minimal entity by hand). Assert the payload does **not** contain the schema heading. This confirms the change is backward-compatible.

Run `uv run pytest tests/test_entities.py -k TestStartupPayloadWikiSchema` — both tests should **fail** at this point (schema content is not yet in the payload).

### Step 2: Extend `startup_payload()` to load and embed the wiki schema

**File**: `src/entities.py`

1. Add a new private helper method `_wiki_schema_content(name: str) -> str` directly below `_wiki_index_content`. It reads `wiki/wiki_schema.md` and returns its full text, or an empty string if the file is absent. Pattern is identical to `_wiki_index_content`:

   ```python
   # Chunk: docs/chunks/entity_wiki_maintenance_prompt - Load full schema into startup payload
   def _wiki_schema_content(self, name: str) -> str:
       schema_path = self.entity_dir(name) / "wiki" / "wiki_schema.md"
       if not schema_path.exists():
           return ""
       return schema_path.read_text().strip()
   ```

2. Inside `startup_payload()`, in the `if self.has_wiki(name):` branch (around line 379), replace the brief "Wiki Maintenance Protocol" block with the full schema content. The updated structure for the wiki section should be:

   ```
   ## Wiki: <name>
   <navigation hint about cat/grep>
   <wiki/index.md content>

   ## Wiki Schema
   <full wiki/wiki_schema.md content>
   ```

   Drop the inline bullet-list triggers (they are now fully covered by the embedded schema). Keep the `Full schema` reference line only if the schema file fails to load (graceful fallback to the old brief block).

3. Add a backreference comment at the method call site:
   ```python
   # Chunk: docs/chunks/entity_wiki_maintenance_prompt - Embed full schema in payload
   ```

Run `uv run pytest tests/test_entities.py -k TestStartupPayloadWikiSchema` — both tests should now **pass**.

Run the full test suite to confirm no regressions: `uv run pytest tests/`.

### Step 3: Strengthen Step 6 in the startup skill template

**File**: `src/templates/commands/entity-startup.md.jinja2`

Replace the current Step 6 block (lines 73–82) with an expanded version that:

- Opens with the **compounding artifact** frame: contrast "rediscovering knowledge each session" (RAG-style) with the wiki that accumulates and stays current.
- States clearly that **the cross-references are the value** — connections between pages compound over time and degrade when orphaned.
- Provides concrete **when → do** triggers (not just a list of nouns):
  - New concept encountered → create/update `domain/` page, add wikilink from any related page
  - Technique applied → create/update `techniques/` page
  - Something was wrong or surprising → update the page **and** add to `identity.md` Hard-Won Lessons
  - Significant decision made → update `projects/` page
  - Session ends → add entry to `log.md`
  - New page created → update `index.md` immediately
- States that **adversity produces the most valuable content** — failures, surprises, corrections are the richest update triggers.
- Reframes wiki maintenance as **part of working, not separate from it** — the schema is already loaded into the startup payload (not a separate read step).

The schema is now embedded in the payload, so the closing line can simply reference "Your wiki schema is in the startup payload above — it is your operational reference for this session."

### Step 4: Strengthen the wiki schema document template

**File**: `src/templates/entity/wiki_schema.md.jinja2`

Two additions to the existing well-structured document:

**A. Add compounding-artifact framing at the top** (after the opening paragraph, before Directory Structure):

```markdown
## Why This Wiki Exists

Most agents rediscover knowledge from scratch each session. This wiki is different:
it is a **persistent, compounding artifact**. When you learn something, integrate it
here — not so you can retrieve it later (though you can), but so that future knowledge
builds on current knowledge rather than replacing it.

**The cross-references are the value.** A page that links to three related pages is
worth more than three isolated pages. Connections compound. Orphaned pages decay.
Maintaining the links is not bookkeeping — it is the primary work of wiki maintenance.
```

**B. Add an explicit Operations section** (after Maintenance Workflow, before Index Maintenance):

```markdown
## Operations

**Ingest.** When something new happens — a new concept, a failure, a decision —
integrate it into the wiki. Read the relevant pages first, then update them with
new knowledge positioned relative to what you already knew. A single event may
touch 3–5 pages. Each update should include or update at least one wikilink.

**Query.** When you need to recall something, read `index.md` first to find
relevant pages, then drill in. Good answers discovered during query — comparisons,
analyses, connections — should be filed back as new or updated pages.
Explorations compound in the wiki just like ingested knowledge does.

**Lint.** Periodically health-check your wiki:
- Pages that reference a concept but lack a corresponding page → create the page
- Pages with no inbound links (orphans) → link from related pages or `index.md`
- Stale claims that later sessions have superseded → update or flag
- Missing cross-references between clearly related pages → add the links
```

### Step 5: Verify the full test suite passes

```
uv run pytest tests/
```

All tests should pass. Spot-check the startup payload manually with a test entity to confirm the schema content appears in output:

```
uv run ve entity startup <any-wiki-entity>
```

## Risks and Open Questions

- **Payload size**: The full schema is ~150 lines. This was explicitly assessed as acceptable in the GOAL.md ("Keep the startup payload reasonable size — full schema is ~150 lines, this is fine"). No risk here.
- **Template re-rendering**: The CLAUDE.md notes that rendered files must be regenerated with `ve init` after template edits. The startup skill template and wiki schema template are source files; run `uv run ve init` after editing them to verify rendering succeeds cleanly.

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
-->