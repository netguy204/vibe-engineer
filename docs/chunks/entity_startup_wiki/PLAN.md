

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Revise `Entities.startup_payload()` in `src/entities.py` to detect whether an entity has a
`wiki/` directory and, if so, load `wiki/index.md` between core memories and the consolidated
index. Add a brief wiki maintenance reminder section pointing to `wiki/wiki_schema.md` so the
entity knows to maintain its wiki in real time without needing a reminder mid-session.

For legacy entities (no `wiki/` directory) the existing payload is emitted unchanged —
backward compatibility is non-negotiable.

The wiki/index.md content itself is the orientation artifact the investigation identified as
the lightweight startup load (structured catalog rather than full pages). The full
`wiki_schema.md` is pointed to by path so the entity can re-read it on demand without
inflating every startup payload.

Wiki schema injection strategy chosen: **include in startup payload output** (the
`ve entity startup <name>` text the agent reads at session start). This is the simplest
approach — no CLAUDE.md mutation, no dynamic file creation — and is consistent with how
the existing touch protocol and active-state instructions are already delivered. The key
content (index + brief rules) is in context from the moment the entity wakes.

The `/entity-startup` skill template also gets updated to match: new steps for wiki
orientation and wiki maintenance are inserted after core memory internalization.

Testing follows TDD: write failing tests first, then implement.

## Sequence

### Step 1: Update `code_paths` in GOAL.md

Add `tests/test_entities.py` to the `code_paths` frontmatter in
`docs/chunks/entity_startup_wiki/GOAL.md`.

### Step 2: Write failing tests — `has_wiki()` helper

In `tests/test_entities.py`, add a new test class `TestHasWiki` with tests:

- `test_has_wiki_true_for_wiki_entity` — entity created with `create_entity()` returns True
  (the wiki schema chunk already makes `create_entity` create a `wiki/` directory)
- `test_has_wiki_false_for_legacy_entity` — manually created entity dir without `wiki/`
  returns False

These tests will fail until `has_wiki()` is implemented in Step 4.

### Step 3: Write failing tests — wiki startup payload

In `tests/test_entities.py`, add a new test class `TestStartupPayloadWiki` with tests:

- `test_wiki_payload_includes_wiki_index_content` — payload for a wiki entity contains the
  text from `wiki/index.md`
- `test_wiki_payload_includes_maintenance_reminder` — payload contains a
  "Wiki Maintenance Protocol" or similar heading
- `test_wiki_payload_references_wiki_schema` — payload mentions `wiki/wiki_schema.md` so
  the entity knows where to find the full schema reference
- `test_wiki_payload_section_order` — verify the ordering: core memories appear before the
  wiki index section, which appears before the consolidated memory index
- `test_legacy_entity_payload_unchanged` — manually create an entity directory without
  `wiki/` (simulating a pre-wiki entity) and assert that the payload does NOT contain any
  "Wiki" heading sections — backward compatibility check

These tests will fail until Steps 4–5 are implemented.

### Step 4: Implement `has_wiki()` helper in `entities.py`

Add a public method on the `Entities` class:

```python
# Chunk: docs/chunks/entity_startup_wiki - Wiki format detection
def has_wiki(self, name: str) -> bool:
    """Return True if the entity has a wiki/ directory (new wiki-based format)."""
    return (self.entity_dir(name) / "wiki").is_dir()
```

Location: `src/entities.py`, placed near `entity_exists()` (other predicate methods).

Run `TestHasWiki` tests — they should pass now.

### Step 5: Revise `startup_payload()` in `entities.py`

Update `startup_payload()` to branch on `has_wiki()`.

**Section ordering for wiki entities** (insert between core memories and consolidated index):

```
## Wiki: <name>

*Your structured knowledge base. Read specific pages during the session with
`cat .entities/<name>/wiki/<path>` or `grep`.*

<full content of wiki/index.md>

## Wiki Maintenance Protocol

Maintain your wiki **during the session, not after**. When you learn something,
update the relevant page immediately — the wiki is a natural byproduct of working.

Key triggers:
- New concept encountered → create/update `wiki/domain/` page
- Technique applied → create/update `wiki/techniques/` page
- Something was wrong → update relevant page + add to `wiki/identity.md` Hard-Won Lessons
- Significant decision made → update `wiki/projects/` page
- Session ends → add entry to `wiki/log.md`
- New page created → update `wiki/index.md`

Full schema and conventions: `wiki/wiki_schema.md`
```

For legacy entities (no `wiki/`), `startup_payload()` emits exactly what it does today —
no wiki sections at all.

Add a `_wiki_index_content(name)` private helper that reads `wiki/index.md` and returns
its full text (or an empty string if the file does not exist), keeping `startup_payload()`
clean.

Add backreference comment on `startup_payload()`:
```python
# Chunk: docs/chunks/entity_startup_wiki - Wiki-aware startup payload
```

Run `TestStartupPayloadWiki` tests — they should pass now. Also confirm all existing
`TestStartupPayload` tests still pass (no regression).

### Step 6: Update skill template `entity-startup.md.jinja2`

Update `src/templates/commands/entity-startup.md.jinja2` to revise the startup steps so
they match the new payload structure and explicitly guide the entity through wiki orientation
and wiki maintenance commitment.

**Revised step sequence** (insert between current Steps 4 and 5):

After "Step 4: Internalize core memories", add:

```
### Step 5: Orient with your wiki

The startup payload includes your **Wiki** section with the content of `wiki/index.md` —
your structured knowledge catalog. Read it to orient: what do you already know that's
relevant to this session's work?

If you need details on a specific topic, read the page directly:

    cat .entities/<name>/wiki/domain/<topic>.md

Or search across your wiki:

    grep -r "<keyword>" .entities/<name>/wiki/

### Step 6: Commit to wiki maintenance

You are a wiki-maintaining entity. During this session:

- Update wiki pages **as you work**, not afterward
- When you learn something, update the relevant page immediately
- Every session ends with a `wiki/log.md` entry
- The full maintenance conventions are at `wiki/wiki_schema.md`

This is not a separate "note-taking" step — it is part of working.
```

Renumber the subsequent steps accordingly (existing 5–8 become 7–10).

For the existing step about the consolidated memory index (new Step 7), update the
introductory line to clarify it's a supplement to the wiki, not the primary knowledge store.

Add backreference comment at the top of the template:
```
{# Chunk: docs/chunks/entity_startup_wiki - Wiki-aware startup skill template #}
```

Run `ve init` to re-render the template into the `.claude/commands/entity-startup.md`
output file.

### Step 7: Run the full test suite

```bash
uv run pytest tests/test_entities.py -v
```

All tests should pass. Fix any regressions before proceeding.

## Dependencies

- **entity_wiki_schema** (ACTIVE): Must be complete — this chunk depends on the wiki
  directory structure (`wiki/`, `wiki/index.md`, `wiki/wiki_schema.md`) being created by
  `create_entity()`. The plan assumes those templates and the `create_entity()` changes
  from that chunk are already in place.

- **entity_attach_detach** (dependency per GOAL frontmatter): The `ve entity attach`
  command places an entity at `.entities/<name>/`. This chunk's `startup_payload()` only
  reads from `self.entity_dir(name)` which is already correctly set up — no additional
  changes needed for attached entities.

## Risks and Open Questions

- **Token budget**: The goal targets under 5K tokens for the startup payload. The wiki
  `index.md` is intentionally lightweight (a catalog table, ~200–400 words). Core memories
  and the maintenance reminder add another ~500 words. For a mature entity with many core
  memories, this could approach the limit. Mitigation: the plan keeps `wiki/index.md`
  as a summary-only catalog (enforced by the schema); deep pages are loaded on-demand.
  If the budget is exceeded in practice, the consolidated memory index can be trimmed to
  titles-only (it already is).

- **Legacy entity detection**: The `has_wiki()` check is a directory existence test.
  This is reliable for the two cases we care about (newly created entities always have
  `wiki/`; pre-schema entities never have it). No edge cases expected.

- **Template re-rendering**: After editing `entity-startup.md.jinja2`, `ve init` must be
  run to regenerate the rendered command file. The `entity_startup_wiki` chunk does not
  own `ve init` — just run it as part of this chunk's implementation.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->