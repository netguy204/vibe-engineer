---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/chunk.py
- tests/test_chunk_list.py
code_references:
  - ref: src/cli/chunk.py#list_chunks
    implements: "CLI chunk list command with external chunk handling and status display"
  - ref: tests/test_chunk_list.py#TestExternalChunkListing
    implements: "Test coverage for external chunk listing behavior"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
created_after:
- chunknaming_drop_ticket
---

# Chunk Goal

## Minor Goal

`ve chunk list` handles external chunk references cleanly. When a chunk directory contains `external.yaml` instead of `GOAL.md`, the command detects the external artifact and displays an `[EXTERNAL: org/repo]` status indicator rather than emitting a parse error.

## Success Criteria

1. `ve chunk list` displays external chunks without parse errors
2. External chunks show a meaningful status indicator (e.g., `[EXTERNAL]` or `[EXTERNAL: org/repo]`)
3. External chunks are properly included in the causal ordering (they have `created_after` in `external.yaml`)
4. Tests added for external chunk listing behavior

## Technical Context

The implementation lives in `src/cli/chunk.py` in the `list_chunks` command. It checks for external artifact references using `is_external_artifact()` before attempting to parse frontmatter:

1. For each chunk directory, the command checks whether it contains `external.yaml` (external reference).
2. If external, the command loads the reference via `load_external_ref()` and displays `EXTERNAL: {repo}` status.
3. If not external, the command proceeds with standard frontmatter parsing and status display.
4. Status filtering skips external chunks when a status filter is active.

Test coverage lives in `TestExternalChunkListing`.
