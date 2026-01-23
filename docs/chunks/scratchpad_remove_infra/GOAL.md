---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models.py
  - src/scratchpad.py
  - src/scratchpad_commands.py
  - src/ve.py
  - src/templates/scratchpad_chunk/GOAL.md.jinja2
  - src/templates/scratchpad_narrative/OVERVIEW.md.jinja2
  - src/templates/commands/migrate-to-subsystems.md.jinja2
  - .claude/commands/migrate-to-subsystems.md
  - tests/test_scratchpad.py
  - tests/test_scratchpad_commands.py
  - tests/conftest.py
code_references:
  - ref: src/models.py
    implements: "Removed ScratchpadChunkStatus, ScratchpadChunkFrontmatter, ScratchpadNarrativeStatus, ScratchpadNarrativeFrontmatter classes"
  - ref: src/ve.py
    implements: "Removed scratchpad CLI command group"
  - ref: tests/conftest.py
    implements: "Removed isolated_scratchpad and scratchpad_for_project fixtures"
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Updated to reflect in-repo workflow instead of scratchpad"
  - ref: src/templates/commands/narrative-create.md.jinja2
    implements: "Updated to reflect in-repo workflow instead of scratchpad"
narrative: revert_scratchpad_chunks
investigation: null
subsystems: []
friction_entries: []
bug_type: null
created_after: ["scratchpad_revert_migrate", "taskdir_context_cmds", "orch_agent_question_tool"]
---

# Chunk Goal

## Minor Goal

Remove all scratchpad infrastructure for chunks and narratives from the codebase.
The previous chunk (`scratchpad_revert_migrate`) migrated artifacts back to `docs/`
and updated CLI commands to work with in-repo locations. This chunk completes the
reversion by deleting the now-unused scratchpad code.

This is pure cleanup - no behavioral changes, just removal of dead code paths that
are no longer reachable after the migration chunk.

## Success Criteria

- All scratchpad chunk/narrative classes deleted from `src/models.py`:
  - `ScratchpadChunkStatus`
  - `ScratchpadChunkFrontmatter`
  - `ScratchpadNarrativeStatus`
  - `ScratchpadNarrativeFrontmatter`

- All scratchpad chunk/narrative classes deleted from `src/scratchpad.py`:
  - `ScratchpadChunks`
  - `ScratchpadNarratives`

- Scratchpad functions removed from `src/scratchpad_commands.py`:
  - Any functions specific to scratchpad chunk/narrative operations

- `/migrate-to-subsystems` skill deleted entirely (it was scratchpad-specific)

- All tests for scratchpad chunk/narrative functionality removed

- Grep for "ScratchpadChunk" in `src/` returns no hits
- Grep for "ScratchpadNarrative" in `src/` returns no hits
- Grep for "scratchpad.*chunk" (case-insensitive) in `src/` returns no hits
- Grep for "scratchpad.*narrative" (case-insensitive) in `src/` returns no hits

- All existing tests pass after removal