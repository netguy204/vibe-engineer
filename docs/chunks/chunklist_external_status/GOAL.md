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

Fix `ve chunk list` to properly handle external chunk references. Currently, when a chunk directory contains `external.yaml` instead of `GOAL.md`, the command fails to parse the chunk and displays:

```
docs/chunks/edp_discount_estimation [PARSE ERROR: Chunk 'edp_discount_estimation' not found]
```

The fix should detect external artifacts and display them appropriately, either showing `[EXTERNAL]` status or resolving the external reference to fetch the actual status from the external repo.

## Success Criteria

1. `ve chunk list` displays external chunks without parse errors
2. External chunks show a meaningful status indicator (e.g., `[EXTERNAL]` or `[EXTERNAL: org/repo]`)
3. External chunks are properly included in the causal ordering (they have `created_after` in `external.yaml`)
4. Tests added for external chunk listing behavior

## Technical Context

The implementation is in `src/cli/chunk.py` in the `list_chunks` command (lines 456-481). The fix checks for external artifact references using `is_external_artifact()` before attempting to parse frontmatter:

1. For each chunk directory, checks if it contains `external.yaml` (external reference)
2. If external, loads the external reference using `load_external_ref()` and displays `EXTERNAL: {repo}` status
3. If not external, proceeds with standard frontmatter parsing and status display
4. Handles status filtering by skipping external chunks when a status filter is active

The fix is completed and tested with comprehensive test coverage in `TestExternalChunkListing`.
