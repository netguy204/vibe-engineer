---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/entity_shutdown.py
- src/cli/entity.py
- tests/test_entity_shutdown.py
- tests/test_entity_shutdown_cli.py
code_references:
- ref: src/entity_shutdown.py#run_consolidation
  implements: "Read existing journal entries from disk and include them in consolidation; delete consolidated journal files after successful API call"
- ref: src/cli/entity.py#shutdown
  implements: "Accept empty input ([] or blank) instead of rejecting it, enabling consolidation of existing journals only"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- entity_memory_decay
- entity_memory_schema
- entity_shutdown_skill
- entity_startup_skill
- entity_touch_command
- orch_retry_single
---

# Chunk Goal

## Minor Goal

Make `ve entity shutdown` consolidate existing journal memories even when no new memories are provided.

Currently, `ve entity shutdown` only consolidates memories passed in via `--memories-file` or stdin. If you pass an empty array, it's a no-op — it doesn't look at the journals already on disk. This means journal entries written directly (e.g., by a steward that couldn't run consolidation due to a missing API key) sit unconsolidated with no way to promote them.

The shutdown command should read existing journal entries from the entity's `memories/journal/` directory and include them in the consolidation pass alongside any new memories from the input. When called with an empty input (`echo '[]' | ve entity shutdown`), it should still consolidate whatever journals exist on disk.

## Success Criteria

- `ve entity shutdown <name>` with empty input consolidates existing journal entries from disk
- Journal entries already on disk are read and fed into the consolidation LLM call
- New memories from `--memories-file` are still written to journal first, then all journals are consolidated together
- Previously consolidated journals are not re-processed (track which journals have been consolidated, e.g., by moving/renaming them or keeping a cursor)
- Tests verify: existing journals are consolidated when no new memories are provided

