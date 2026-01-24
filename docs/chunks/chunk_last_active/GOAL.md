---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/chunks.py
  - src/ve.py
  - src/templates/commands/chunk-commit.md.jinja2
  - tests/test_chunks.py
  - tests/test_chunk_list.py
code_references:
  - ref: src/chunks.py#Chunks::get_last_active_chunk
    implements: "Core ACTIVE tip lookup with mtime-based selection"
  - ref: src/ve.py#list_chunks
    implements: "CLI handler with --last-active flag and mutual exclusivity check"
  - ref: src/ve.py#_list_task_chunks
    implements: "Cross-repo (task context) support for --last-active"
  - ref: src/templates/commands/chunk-commit.md.jinja2
    implements: "Fallback pattern using --last-active when --latest fails"
  - ref: tests/test_chunks.py#TestGetLastActiveChunk
    implements: "Unit tests for get_last_active_chunk method"
  - ref: tests/test_chunk_list.py#TestLastActiveFlag
    implements: "CLI tests for --last-active flag"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
created_after: ["backref_restore_postmigration"]
---

# Chunk Goal

## Minor Goal

Add a `--last-active` flag to `ve chunk list` that returns the most recently
completed ACTIVE chunk. The selection criteria are:

1. Must be ACTIVE status
2. Must be a "tip" in the causal ordering (no other chunks have it in their
   `created_after` field)
3. Among qualifying chunks, select the one with the most recent GOAL.md mtime

This two-part filter avoids false positives: during chunk-complete, other ACTIVE
chunks might be edited (e.g., updating references or marking as SUPERSEDED), but
only the just-completed chunk will be both a tip AND have the most recent mtime.

This fixes a workflow gap: after running `/chunk-complete`, the chunk status
changes to ACTIVE, so `ve chunk list --latest` (which only finds IMPLEMENTING
chunks) can no longer identify it. The `/chunk-commit` skill uses `--latest`
to provide context for commit messages, but fails to identify the just-completed
chunk.

With `--last-active`, the chunk-commit template can fall back to this when
`--latest` returns nothing, ensuring commit context is always available.

## Success Criteria

1. `ve chunk list --last-active` returns the ACTIVE tip chunk with the most
   recent GOAL.md mtime, outputting `docs/chunks/<chunk_name>`
2. When no ACTIVE tip chunks exist, outputs an error message to stderr and exits 1
3. The chunk-commit template uses `--last-active` as a fallback when `--latest`
   returns nothing
4. Unit tests cover:
   - Finding ACTIVE tip with most recent mtime
   - Multiple ACTIVE tips (returns most recent by mtime)
   - ACTIVE chunk that is not a tip (should be excluded)
   - No ACTIVE chunks (error case)
5. The `--latest` and `--last-active` flags are mutually exclusive

