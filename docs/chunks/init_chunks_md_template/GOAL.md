---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/trunk/CHUNKS.md.jinja2
- tests/test_init.py
code_references:
  - ref: src/templates/trunk/CHUNKS.md.jinja2
    implements: "Jinja2 template rendered by ve init to produce docs/trunk/CHUNKS.md, containing the four chunk principles"
  - ref: tests/test_init.py#TestInitCommand::test_init_creates_chunks_md
    implements: "Integration test verifying ve init creates docs/trunk/CHUNKS.md with correct content"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- narrative_proposed_chunks_doc
---

# Chunk Goal

## Minor Goal

`ve init` populates a trunk doc set that includes `docs/trunk/CHUNKS.md`,
making the four chunk principles (intent ownership, present-tense GOAL.md,
chunk DAG, etc.) available on every project that follows the documented
onboarding path.

`src/templates/trunk/` ships nine `.jinja2` files — ARTIFACTS, CHUNKS,
DECISIONS, EXTERNAL, FRICTION, GOAL, ORCHESTRATOR, SPEC,
TESTING_PHILOSOPHY — and `_init_trunk` in `src/project.py` renders the
entire directory on `ve init`. `src/templates/trunk/CHUNKS.md.jinja2`
contains the four chunk principles as static prose; no Jinja2 variable
substitutions are required.

The `/audit-intent` skill's first prerequisite check (`test -f
docs/trunk/CHUNKS.md`) passes on every project initialized by `ve init`,
because `docs/trunk/CHUNKS.md` is part of the rendered trunk set.

## Success Criteria

- `src/templates/trunk/CHUNKS.md.jinja2` exists and renders to faithful
  CHUNKS.md content (the four principles as currently expressed in
  `docs/trunk/CHUNKS.md` of this repository).
- `ve init` on a fresh project directory produces `docs/trunk/CHUNKS.md`
  alongside the other 8 trunk docs (verified by an integration test or by
  running `ve init` in a tmp directory).
- The `/audit-intent` skill's first prerequisite check (`test -f
  docs/trunk/CHUNKS.md`) passes on any project produced by `ve init`.
- Re-running `ve init` on a project that already has `docs/trunk/CHUNKS.md`
  preserves the existing file (the `overwrite=False` semantics of
  `_init_trunk` already guarantee this — the chunk does not regress that
  behavior).
- This repository's own `docs/trunk/CHUNKS.md` continues to render
  identically after `ve init` (so the source-of-truth file stays in sync
  with what new projects receive).

## Out of Scope

- Changing the four principles themselves, or the wording of CHUNKS.md
  content.
- Adding the integration test that exercises "ve init → ve chunk create →
  ve chunk activate → ve chunk complete → audit-intent" end-to-end. That
  was suggested by the reporter as a meta-protection against template/skill
  drift but is a separate initiative; this chunk only fixes the missing
  template.
- Updating other trunk docs or skill prerequisites.