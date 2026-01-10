---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/templates/commands/chunk-create.md.jinja2
- .claude/commands/chunk-create.md
- README.md
- docs/subsystems/workflow_artifacts/OVERVIEW.md
code_references:
- ref: src/ve.py#create
  implements: "Primary chunk creation CLI command (renamed from start) with backward-compatible start alias"
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["external_chunk_causal"]
---

# Chunk Goal

## Minor Goal

Rename the CLI command `ve chunk start` to `ve chunk create` for consistency with
other workflow artifact commands (`ve narrative create`, `ve investigation create`,
`ve subsystem discover`).

This addresses a known deviation documented in the workflow_artifacts subsystem:
"CLI Command Inconsistency: `chunk start` vs `create`". The subsystem's soft
convention states "CLI command naming: `ve {type} create`" for consistent command
structure aiding discoverability.

The change maintains backward compatibility by keeping `start` as an alias for
`create`, ensuring existing documentation and muscle memory continue to work.

## Success Criteria

1. `ve chunk create <shortname>` works identically to current `ve chunk start <shortname>`
2. `ve chunk start <shortname>` continues to work as an alias (backward compatibility)
3. `ve chunk --help` shows `create` as the primary command with `start` as alias
4. All slash commands that reference `chunk start` are updated to reference `chunk create`
5. The workflow_artifacts subsystem OVERVIEW.md code reference for `src/ve.py#start` is
   updated to reflect the new command name
6. The known deviation "CLI Command Inconsistency: `chunk start` vs `create`" is resolved
   (removed from subsystem docs)
7. All tests pass

