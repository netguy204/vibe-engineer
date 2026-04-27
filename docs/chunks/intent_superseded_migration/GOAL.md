---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- docs/chunks/integrity_deprecate_standalone/GOAL.md
- docs/chunks/jinja_backrefs/GOAL.md
- docs/chunks/narrative_backreference_support/GOAL.md
- docs/chunks/proposed_chunks_frontmatter/GOAL.md
- docs/chunks/scratchpad_chunk_commands/GOAL.md
- docs/chunks/scratchpad_cross_project/GOAL.md
- docs/chunks/scratchpad_narrative_commands/GOAL.md
- docs/chunks/scratchpad_storage/GOAL.md
- docs/chunks/subsystem_template/GOAL.md
- docs/chunks/template_drift_prevention/GOAL.md
- docs/chunks/update_crossref_format/GOAL.md
- docs/chunks/websocket_keepalive/GOAL.md
code_references:
  - ref: docs/chunks/integrity_deprecate_standalone/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/jinja_backrefs/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/narrative_backreference_support/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/proposed_chunks_frontmatter/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/scratchpad_chunk_commands/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/scratchpad_cross_project/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/scratchpad_narrative_commands/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/scratchpad_storage/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/subsystem_template/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/template_drift_prevention/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/update_crossref_format/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
  - ref: docs/chunks/websocket_keepalive/GOAL.md
    implements: "Migrated from SUPERSEDED to HISTORICAL"
narrative: intent_ownership
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- intent_principles
---

# Chunk Goal

## Minor Goal

Twelve chunks that formerly carried `status: SUPERSEDED` now carry status values from the five-status taxonomy in `docs/trunk/CHUNKS.md`. All twelve are HISTORICAL — their intent was replaced or abandoned. No chunk in `docs/chunks/` carries SUPERSEDED, clearing the way for the `intent_retire_superseded` chunk to remove SUPERSEDED from the runtime.

The twelve migrated chunks:
- `integrity_deprecate_standalone`
- `jinja_backrefs`
- `narrative_backreference_support`
- `proposed_chunks_frontmatter`
- `scratchpad_chunk_commands`
- `scratchpad_cross_project`
- `scratchpad_narrative_commands`
- `scratchpad_storage`
- `subsystem_template`
- `template_drift_prevention`
- `update_crossref_format`
- `websocket_keepalive`

Each chunk's classification was reviewed against two heuristics:
- **HISTORICAL** if the chunk's intent was replaced by another chunk or commit and is no longer in force.
- **COMPOSITE** if the chunk still owns part of the intent that governs current code, shared with peer chunks.

All twelve fell into HISTORICAL. Existing `superseded_by` and `superseded_reason` frontmatter fields are preserved for traceability. Chunks without those fields received prose notes explaining the replacement context.

## Success Criteria

1. Each of the 12 chunks is classified as HISTORICAL or COMPOSITE under the new taxonomy.
2. Each chunk's `status` field reflects its new value.
3. Traceability to the replacement is preserved (via `superseded_by`/`superseded_reason` fields, or prose notes).
4. `grep -l "^status: SUPERSEDED" docs/chunks/*/GOAL.md` returns nothing.
5. `uv run pytest tests/` passes.