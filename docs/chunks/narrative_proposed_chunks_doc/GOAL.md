---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/narrative/OVERVIEW.md.jinja2
- src/templates/commands/narrative-create.md.jinja2
code_references:
- ref: src/templates/narrative/OVERVIEW.md.jinja2
  implements: "Corrected PROPOSED_CHUNKS comment block instructing agents to populate at narrative-creation time"
- ref: src/templates/commands/narrative-create.md.jinja2
  implements: "Updated Step 3 to explicitly direct agents to populate proposed_chunks frontmatter during narrative creation"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- watch_reconnect_counter_reset
---

# Chunk Goal

## Minor Goal

The narrative OVERVIEW.md template (`src/templates/narrative/OVERVIEW.md.jinja2`)
and the `/narrative-create` skill prompt
(`src/templates/commands/narrative-create.md.jinja2`) give consistent guidance:
agents populate `proposed_chunks` at narrative-creation time.

The OVERVIEW.md template's `PROPOSED_CHUNKS` comment block instructs agents to
populate the array at creation time, documents which fields are set when
(`prompt` and `depends_on` at creation, `chunk_directory` left null until
reification by `/chunk-create`), and preserves the `depends_on` semantics table
(null vs [] vs indices). Step 3 of the skill prompt explicitly states that
completing the template includes writing the `proposed_chunks` frontmatter array.

`proposed_chunks` entries enumerate unreified chunks in the PROPOSED state,
which is the affordance that lets `ve chunk list-proposed` surface work the
operator has spec'd but not yet `/chunk-create`d. Leaving the array empty
defeats this discovery surface.

## Success Criteria

- `src/templates/narrative/OVERVIEW.md.jinja2`'s `proposed_chunks` frontmatter
  comment block is rewritten so that it instructs the agent to populate the
  array at narrative-creation time. The "DO NOT POPULATE" instruction is
  removed.
- The rewritten template comment is internally consistent with the
  `depends_on` semantics already documented in the same file (null vs []
  vs indices) and with Step 4 of the `/narrative-create` skill prompt.
- The rewritten template comment clarifies which fields are populated when:
  - `prompt`: at narrative-creation time
  - `depends_on`: at narrative-creation time (per documented semantics)
  - `chunk_directory`: stays `null` at narrative-creation time and is filled
    in by `/chunk-create` when the proposed chunk is reified
- `src/templates/commands/narrative-create.md.jinja2` Step 4 remains
  authoritative on `depends_on` semantics; if any wording in Step 4 implied
  the template should be left empty, it is corrected.
- After re-rendering with `ve init`, the rendered files (the project's own
  CLAUDE.md / .claude/commands/narrative-create.md and any
  rendered narrative OVERVIEW.md template surfaces) reflect the corrected
  guidance.
- A fresh `ve narrative create <name>` produces an OVERVIEW.md whose inline
  comments tell a single, coherent story: populate `proposed_chunks` now,
  with `chunk_directory: null` until reified.

## Out of Scope

- Changing the `proposed_chunks` schema itself (field names, structure,
  validator behavior). This chunk only reconciles documentation/guidance.
- Backfilling existing narratives that were created with empty
  `proposed_chunks` arrays. Operators can edit those by hand.