

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Two strings need updating. Both live in the Touch Protocol documentation
that is emitted to agents at entity startup:

1. **`src/entities.py` → `startup_payload()`** — The Touch Protocol section
   (around line 452–455) currently says the ID format is like
   `20260319_core_memory`. Update the prose and parenthetical example to
   acknowledge that the ID is whatever the `ID:` field shows next to each
   core memory — the format varies by entity type (timestamp-prefixed for
   tiered-memory entities, slug for wiki-based entities).

2. **`src/templates/commands/entity-startup.md.jinja2` → Step 8** — The
   concrete `ve entity touch` example (line 137) hard-codes a
   timestamp-prefixed ID. Add a second example that shows the wiki-slug
   shape, and add a brief note that the ID to use is whatever the startup
   payload shows in the `ID:` field.

No new files, no structural changes, no new tests required — this is a
pure documentation-in-code update. Existing tests that snapshot
`startup_payload` output do not lock in the example strings (they test
structure, not prose content), so no test changes are expected.

If a snapshot test does fail, update the snapshot to match the new prose.

## Subsystem Considerations

No subsystems are relevant.

## Sequence

### Step 1: Update Touch Protocol prose in `src/entities.py`

**Location:** `src/entities.py`, `startup_payload()` method, the
`## Touch Protocol` section (currently lines 449–459).

Current text (paraphrased):
> "Use the ID shown next to each core memory above (e.g.,
> `ve entity touch <name> 20260319_core_memory "applied this insight"`)."

Replace with prose that:
- States the `memory_id` to use is whatever the `ID:` field shows next
  to each core memory in the startup payload above.
- Notes that the format varies by entity type: timestamp-prefixed IDs
  (e.g., `20260319_core_memory`) for tiered-memory entities, and slug
  IDs (e.g., `trust-the-canonical-synthesis`) for wiki-based entities.
- Keeps the overall sentence tight — no new paragraphs, just a
  clarifying parenthetical.

Add backreference comment before the Touch Protocol section:
```python
# Chunk: docs/chunks/touch_docs_wiki_ids - Touch Protocol examples cover both ID formats
```

### Step 2: Update Step 8 example in `entity-startup.md.jinja2`

**Location:** `src/templates/commands/entity-startup.md.jinja2`, Step 8
(currently lines 124–138).

Current example:
```
ve entity touch aria 20260414_120742_089450_template_editing_workflow "Used template editing workflow to fix rendering issue"
```

Replace with two examples — one timestamp-prefixed, one slug — plus a
note that the ID is whatever the startup payload's `ID:` field shows:

```
# Tiered-memory entity (timestamp-prefixed ID):
ve entity touch aria 20260414_120742_089450_template_editing_workflow "Used template editing workflow to fix rendering issue"

# Wiki-based entity (slug ID):
ve entity touch aria trust-the-canonical-synthesis "Applied synthesis principle when resolving conflicting signals"
```

And add a note immediately before the code block:
> The `memory_id` is whatever the `ID:` field shows next to each core
> memory in the startup payload above. The format varies by entity type.

Add Jinja2 comment backreference:
```
{# Chunk: docs/chunks/touch_docs_wiki_ids - Touch Protocol examples cover both ID formats #}
```

### Step 3: Run tests

```
uv run pytest tests/ -x -q
```

If any snapshot tests fail due to the updated prose, update the
snapshots to match (`--snapshot-update` flag or equivalent). Confirm
no functional tests break.

## Dependencies

None.

## Risks and Open Questions

- Snapshot tests (if any) may need updating — low risk, straightforward
  to update.
- The example slug IDs (`trust-the-canonical-synthesis`,
  `cloud-capital-roll-call`) are real wiki IDs from the GOAL description
  and serve as recognizable examples. If the operator prefers a generic
  placeholder, substitute `<slug-id>` instead.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
