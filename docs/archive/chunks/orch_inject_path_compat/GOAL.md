---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/ve.py
  - tests/test_chunk_validate_inject.py
code_references:
  - ref: src/ve.py#orch_inject
    implements: "Path normalization using strip_artifact_path_prefix() for CLI consistency"
  - ref: tests/test_chunk_validate_inject.py#TestOrchInjectPathNormalization
    implements: "Test coverage for path normalization behavior across formats"
narrative: null
investigation: null
subsystems: []
created_after:
- chunk_create_guard
- orch_attention_reason
- orch_inject_validate
- deferred_worktree_creation
---

# Chunk Goal

## Minor Goal

Improve the orchestrator's `inject` command to accept full chunk paths (e.g., `docs/chunks/my_chunk/`) in addition to just short names (e.g., `my_chunk`). This aligns with the convention used by other `ve` commands that permissively accept either full paths or short names for their respective artifacts.

## Success Criteria

1. **`ve orch inject` accepts full paths** - Running `ve orch inject docs/chunks/my_chunk/` works identically to `ve orch inject my_chunk`

2. **Path normalization handles variations** - The command correctly handles:
   - With or without trailing slash: `docs/chunks/foo/` and `docs/chunks/foo`
   - Relative paths from project root: `docs/chunks/foo`
   - Artifact/short name syntax: `chunk/foo`
   - Short names: `foo`

3. **Error messages remain clear** - Invalid paths or non-existent chunks produce helpful error messages

4. **Tests cover the new behavior** - Unit tests verify both path formats work correctly

