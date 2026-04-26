<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation-only migration: change `status: SUPERSEDED` to `status: HISTORICAL` (or, rarely, `COMPOSITE`) in 12 chunk GOAL.md files, and preserve replacement traceability. No source code changes.

**Strategy:** For each of the 12 chunks, read its GOAL.md, identify why it was superseded (from `superseded_by` field, `superseded_reason` field, or prose context), classify under the new taxonomy (almost certainly HISTORICAL for all 12), present the classification and reasoning to the operator, then apply on confirmation.

**Traceability:** Three of the 12 chunks already have a `superseded_by:` field in frontmatter (`integrity_deprecate_standalone`, `template_drift_prevention`, `websocket_keepalive`). One has `superseded_reason:` (`narrative_backreference_support`). One has `superseded_by:` as a prose-style note (`update_crossref_format`). The Pydantic `ChunkFrontmatter` model does not define these fields, but its default config (`{}`) silently ignores extras — so these fields parse without error and persist in YAML. For the remaining chunks without any traceability field, a brief `<!-- Replaced by: ... -->` HTML comment will be added to the goal prose explaining the replacement context.

**Validation note:** The `ve chunk validate` command is completion-focused (requires IMPLEMENTING or ACTIVE). HISTORICAL is a terminal state that is never "completed," so this command will always report a status error for HISTORICAL chunks. Success criterion #6 should be interpreted as: frontmatter parses without error (Pydantic model accepts it) and `IntegrityValidator.validate_chunk()` reports no errors for outbound references. We verify this by running `uv run pytest tests/` (criterion #7) and by confirming `grep -l "^status: SUPERSEDED" docs/chunks/*/GOAL.md` returns nothing (criterion #5).

**State machine:** `VALID_CHUNK_TRANSITIONS` in `src/models/chunk.py` already includes `SUPERSEDED → {HISTORICAL}`, so the transition is valid.

No new tests are needed — this chunk modifies only documentation frontmatter. Per `docs/trunk/TESTING_PHILOSOPHY.md`, tests verify behavior, not document content. The existing test suite (`uv run pytest tests/`) confirms the frontmatter model still parses all chunks correctly after migration.

## Sequence

### Step 1: Prepare the classification table

Read each of the 12 SUPERSEDED chunk GOAL.md files and build a classification table with columns: chunk name, current traceability info (superseded_by / superseded_reason / prose), recommended new status, and reasoning.

**Pre-analysis (from planning-time reading):**

All 12 are **HISTORICAL** — every one describes intent that has been replaced, abandoned, or subsumed by other work. None co-own intent with active peers (the COMPOSITE test).

| Chunk | Replacement context | Traceability |
|-------|-------------------|--------------|
| `integrity_deprecate_standalone` | `superseded_by: integrity_deprecated_removal` | ✅ has field |
| `jinja_backrefs` | `superseded_by: "Commit a465762 (refactor: remove chunk/narrative backreferences, simplify subsystems)"` | ✅ has field |
| `narrative_backreference_support` | `superseded_reason: "Narrative backreferences in source code were removed as a design decision..."` | ✅ has field |
| `proposed_chunks_frontmatter` | Standardized proposed_chunks format — work was completed and chunk is no longer the authority | Needs prose note |
| `scratchpad_storage` | Part of `global_scratchpad` narrative — scratchpad approach was abandoned | Needs prose note |
| `scratchpad_chunk_commands` | Part of `global_scratchpad` narrative — scratchpad approach was abandoned | Needs prose note |
| `scratchpad_cross_project` | Part of `global_scratchpad` narrative — scratchpad approach was abandoned | Needs prose note |
| `scratchpad_narrative_commands` | Part of `global_scratchpad` narrative — scratchpad approach was abandoned | Needs prose note |
| `subsystem_template` | Template content was refactored in commit a465762; Chunk Relationships and Consolidation Chunks sections removed | Needs prose note |
| `template_drift_prevention` | `superseded_by: template_lang_agnostic` | ✅ has field |
| `update_crossref_format` | `superseded_by: "scratchpad_remove_infra - Chunk backreferences were eliminated entirely..."` | ✅ has field |
| `websocket_keepalive` | `superseded_by: websocket_hibernation_compat` | ✅ has field |

### Step 2: Present classifications to the operator

Present the full table to the operator with the recommendation that all 12 are HISTORICAL. Wait for confirmation or overrides per chunk before proceeding.

### Step 3: Apply status changes to chunks with existing traceability

For the 7 chunks that already have `superseded_by` or `superseded_reason` fields, the traceability is already preserved in frontmatter. For each:

1. Change `status: SUPERSEDED` → `status: HISTORICAL` in the YAML frontmatter
2. Leave the `superseded_by` / `superseded_reason` field in place (Pydantic ignores it; it serves as archaeological context for humans and agents reading the file)

Chunks: `integrity_deprecate_standalone`, `jinja_backrefs`, `narrative_backreference_support`, `template_drift_prevention`, `update_crossref_format`, `websocket_keepalive`

Note: `jinja_backrefs` has `superseded_by` at line 14 (after `created_after`), which is a non-standard position. Leave as-is — field order in YAML doesn't affect parsing.

### Step 4: Apply status changes to chunks needing prose traceability

For the 5 chunks without a `superseded_by` field, change the status and add a brief HTML comment after the `# Chunk Goal` heading explaining the replacement context:

1. `proposed_chunks_frontmatter` — Add: `<!-- HISTORICAL: The proposed_chunks standardization was completed and merged. This chunk no longer owns active intent. -->`
2. `scratchpad_storage` — Add: `<!-- HISTORICAL: The global_scratchpad narrative and its scratchpad approach were abandoned. Chunks remain in-repo under docs/chunks/. -->`
3. `scratchpad_chunk_commands` — Same scratchpad note as above.
4. `scratchpad_cross_project` — Same scratchpad note as above.
5. `scratchpad_narrative_commands` — Same scratchpad note as above.
6. `subsystem_template` — Add: `<!-- HISTORICAL: Template content was substantially refactored in commit a465762. Chunk Relationships and Consolidation Chunks sections were removed from the subsystem template. The planning template's Subsystem Considerations section persists. -->`

### Step 5: Verify the migration

Run verification commands:

1. `grep -l "^status: SUPERSEDED" docs/chunks/*/GOAL.md` — should return nothing
2. `grep -l "^status: HISTORICAL" docs/chunks/*/GOAL.md` — should include all 12 migrated chunks (plus any previously HISTORICAL chunks)
3. `uv run pytest tests/` — all tests pass

### Step 6: Spot-check frontmatter parsing

For 2-3 of the migrated chunks, verify frontmatter parses correctly by running a quick Python check that the `ChunkFrontmatter` model accepts the updated YAML. This catches any YAML formatting errors introduced during editing.

```bash
uv run python -c "
from models.chunk import ChunkFrontmatter
from chunks import Chunks
import pathlib
c = Chunks(pathlib.Path('.'))
for name in ['integrity_deprecate_standalone', 'scratchpad_storage', 'websocket_keepalive']:
    fm = c.parse_chunk_frontmatter(name)
    print(f'{name}: status={fm.status}')
"
```

## Dependencies

- **`intent_principles`** (IMPLEMENTING) — Lands `docs/trunk/CHUNKS.md` and adds HISTORICAL/COMPOSITE to the runtime enum. Must be merged first so the five-status taxonomy exists. The state machine transition `SUPERSEDED → HISTORICAL` is already in `src/models/chunk.py`.

## Risks and Open Questions

- **`ve chunk validate` reports errors for HISTORICAL chunks.** This is expected behavior (completion validation requires IMPLEMENTING/ACTIVE). Success criterion #6 needs to be interpreted as "frontmatter is valid" rather than "completion validation passes." If the operator wants strict `ve chunk validate` to pass, the validate command would need a mode that checks only frontmatter validity — but that's out of scope for this chunk.

- **Extra frontmatter fields (`superseded_by`, `superseded_reason`).** These are not in the Pydantic model but are silently ignored (default `model_config = {}`). If a future change sets `model_config = ConfigDict(extra="forbid")`, these fields would cause parse errors. This is acceptable — the intent_retire_superseded chunk (chunk 7) should clean up SUPERSEDED-related fields when it retires the status from the runtime.

- **Operator may want to rewrite some goals while migrating.** The GOAL.md explicitly puts goal rewriting out of scope. If the operator notices retrospective framing during the review, note it for the `intent_active_audit` chunk (chunk 6) rather than fixing it here.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->