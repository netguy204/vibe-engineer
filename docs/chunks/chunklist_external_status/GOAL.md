---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- tests/test_chunk_list.py
code_references:
  - ref: src/ve.py#list_chunks
    implements: "External chunk detection and EXTERNAL status display logic"
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

The issue is in `src/ve.py` in the `list_chunks` command. It calls `parse_chunk_frontmatter_with_errors()` which:

1. Calls `get_chunk_goal_path()` to get the path to `GOAL.md`
2. Checks `if goal_path is None or not goal_path.exists()`
3. For external chunks, `GOAL.md` doesn't exist (only `external.yaml`), so it returns the error

The fix should check `is_external_artifact()` from `external_refs.py` before attempting to parse frontmatter, and handle external chunks with an appropriate display.
