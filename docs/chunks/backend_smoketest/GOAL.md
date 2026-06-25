---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- docs/cursor_smoketest.md
code_references:
- ref: docs/cursor_smoketest.md
  implements: "Cursor backend e2e smoketest confirmation marker"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: uses
friction_entries: []
depends_on: []
created_after:
- backend_config
- backend_cursor
- backend_logparse
- backend_parity
---
# Chunk Goal

## Minor Goal

A marker file `docs/cursor_smoketest.md` exists containing a single line confirming the orchestrator's Cursor (Composer) backend executed a chunk end-to-end. Throwaway probe — retained as historical evidence that the Cursor backend path completed at least one chunk end-to-end.

## Success Criteria

- `docs/cursor_smoketest.md` exists with one confirmation line.

## Rejected Ideas

### Anything non-trivial

Deliberately minimal.
