---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- tests/test_entity_shutdown_cli.py
code_references:
- ref: src/cli/entity.py#resolve_entity_project_dir
  implements: "Project root resolution for entity commands"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- entity_consolidate_existing
---

# Chunk Goal

## Minor Goal

Fix `ve entity shutdown` silently reporting success while writing no journal files to disk.

The command reports "Journals added: 17" but the `memories/journal/` directory is empty afterward. The entity exists, the directories exist, the input JSON is valid — yet nothing is persisted. The most likely cause is a project-dir resolution issue (similar to the CWD bugs fixed in board_cursor_root_resolution and orch_daemon_root_resolution): the command may be writing journals to a different `.entities/` directory than where the entity was created, or the Entities instance is constructed with the wrong root path.

Investigation should check:
1. Whether `--project-dir` is being respected or defaulting incorrectly
2. Whether the Entities instance resolves `.entities/` relative to CWD vs the project root
3. Whether the consolidation step (which now deletes consolidated journals per entity_consolidate_existing) is deleting the journals immediately after writing them even when consolidation fails or is skipped

Reported by an external steward running from a different project directory.

## Success Criteria

- `ve entity shutdown` actually writes journal files to the entity's `memories/journal/` directory
- Files are verifiable on disk after the command reports success
- The command fails with a clear error if the entity doesn't exist at the resolved path
- Tests verify journal files exist on disk after shutdown completes

