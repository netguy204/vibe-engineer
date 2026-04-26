---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- src/chunks.py
- src/consolidation.py
- src/cli/chunk.py
- src/task_utils.py
- tests/test_task_utils.py
code_references:
  - ref: src/frontmatter.py#update_frontmatter_field
    implements: "Canonical source for frontmatter field updates; all imports now resolve here directly"
narrative: arch_decompose
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- chunks_decompose
- orch_worktree_cleanup
- validation_error_surface
- validation_length_msg
- orch_ready_critical_path
- orch_pre_review_rebase
- orch_merge_before_delete
---

# Chunk Goal

## Minor Goal

All imports of `update_frontmatter_field` resolve to a single canonical source: `src/frontmatter.py`. The function is defined there and every caller imports it directly, with no re-export indirection through `task_utils.py` or any other module.

This single-source rule eliminates an unnecessary indirection layer, making the codebase easier to navigate for both agents and humans. It is an independent constraint within the `arch_decompose` narrative that keeps the coupling surface of `task_utils.py` minimal as part of the broader module decomposition effort.

## Success Criteria

- Every import of `update_frontmatter_field` in the codebase resolves directly to `from frontmatter import update_frontmatter_field`. No module imports it from `task_utils`.
- The re-export line in `src/task_utils.py` (line 303: `from frontmatter import update_frontmatter_field`) and its associated comment are removed.
- The following five call sites are updated to import from `frontmatter` instead of `task_utils`:
  - `src/chunks.py` (two local imports, lines 317 and 1221)
  - `src/orchestrator/scheduler.py` (top-level import, line 33)
  - `src/consolidation.py` (local import, line 55)
  - `src/cli/chunk.py` (local import, line 638)
- A grep for `from task_utils import update_frontmatter_field` returns zero results.
- All existing tests pass (`uv run pytest tests/`).

