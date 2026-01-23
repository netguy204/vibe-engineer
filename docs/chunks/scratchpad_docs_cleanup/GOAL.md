---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/claude/CLAUDE.md.jinja2
  - src/templates/commands/chunk-create.md.jinja2
  - src/templates/commands/narrative-create.md.jinja2
  - src/templates/commands/narrative-compact.md.jinja2
  - src/templates/chunk/PLAN.md.jinja2
  - src/templates/task/CLAUDE.md.jinja2
  - src/templates/subsystem/OVERVIEW.md.jinja2
code_references:
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Backreference section updated to remove scratchpad language"
  - ref: src/templates/commands/narrative-compact.md.jinja2
    implements: "Background and Phase 4 sections updated to remove scratchpad references"
  - ref: src/templates/chunk/PLAN.md.jinja2
    implements: "Backreference comments section updated to remove scratchpad language"
  - ref: src/templates/task/CLAUDE.md.jinja2
    implements: "Backreferences section updated to remove scratchpad language"
  - ref: src/templates/subsystem/OVERVIEW.md.jinja2
    implements: "Backreference comments section updated to remove scratchpad language"
narrative: revert_scratchpad_chunks
investigation: null
subsystems: []
friction_entries: []
bug_type: null
created_after: ["scratchpad_remove_infra"]
---

# Chunk Goal

## Minor Goal

Update all documentation templates to remove references to user-global scratchpad
storage (`~/.vibe/scratchpad/`) for chunks and narratives. After the previous chunks
in the `revert_scratchpad_chunks` narrative migrated artifacts back to `docs/` and
removed the scratchpad infrastructure, the documentation still contains outdated
references that confuse agents.

This is the final chunk in the narrative - completing it restores full consistency
between the codebase behavior and its documentation.

## Success Criteria

- All templates updated to describe in-repo storage:
  - `src/templates/claude/CLAUDE.md.jinja2`: Remove "ephemeral work notes in user-global scratchpad" language for chunks/narratives
  - `src/templates/commands/chunk-create.md.jinja2`: Already updated in previous chunk (verify)
  - `src/templates/commands/narrative-create.md.jinja2`: Already updated in previous chunk (verify)
  - `src/templates/commands/narrative-compact.md.jinja2`: Update scratchpad references
  - `src/templates/chunk/PLAN.md.jinja2`: Update "user-global scratchpad" reference
  - `src/templates/task/CLAUDE.md.jinja2`: Update "user-global scratchpad" reference
  - `src/templates/subsystem/OVERVIEW.md.jinja2`: Update "user-global scratchpad" reference

- Re-render templates by running `uv run ve init`

- Grep for "scratchpad" in `src/templates/` returns no hits (case-insensitive)
- Grep for "scratchpad" in `.claude/commands/` returns no hits (case-insensitive)

- CLAUDE.md accurately describes chunks/narratives as living in `docs/chunks/` and `docs/narratives/`