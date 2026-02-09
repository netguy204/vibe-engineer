---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/chunk.py
- src/cli/utils.py
- src/task_utils.py
- src/task/__init__.py
- src/orchestrator/models.py
- src/external_resolve.py
- src/cluster_analysis.py
- src/cli/narrative.py
- src/cli/subsystem.py
- src/cli/investigation.py
- src/cli/external.py
- src/cli/friction.py
- src/cli/artifact.py
- src/chunk_validation.py
- src/chunks.py
- tests/test_task_narrative_create.py
- tests/test_task_subsystem_discover.py
- tests/test_task_utils.py
- tests/test_task_context_cmds.py
- tests/test_task_init.py
- tests/test_task_investigation_create.py
- tests/test_task_chunk_create.py
- tests/test_external_resolve.py
- tests/test_chunk_list_proposed.py
- tests/test_artifact_promote.py
- tests/test_artifact_remove_external.py
- tests/test_artifact_copy_external.py
code_references:
  - ref: src/cli/chunk.py#create
    implements: "Removed redundant validate_combined_chunk_name call, migrated task_utils imports to task package"
  - ref: src/cli/utils.py#validate_short_name
    implements: "Deleted validate_combined_chunk_name function (was redundant with validate_short_name)"
  - ref: src/task/__init__.py
    implements: "Task package now serves as the canonical import path (task_utils.py shim deleted)"
narrative: arch_review_gaps
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- cli_decompose
- integrity_deprecate_standalone
- low_priority_cleanup
- optimistic_locking
- spec_and_adr_update
- test_file_split
- orch_session_auto_resume
---

# Chunk Goal

## Minor Goal

Remove dead and redundant code identified during the architecture review, reducing maintenance burden and eliminating confusion for future contributors. This chunk addresses three specific items:

1. **Delete `_start_task_chunk`** (`src/cli/chunk.py`, line 220): This single-chunk creation handler for task directories is defined but never called. The batch version `_start_task_chunks` (line 256) already handles both single and multi-chunk cases by iterating over a list. The dead function is a vestige from before batch creation was introduced and can be safely removed.

2. **Remove `validate_combined_chunk_name`** (`src/cli/utils.py`, line 30): This function accepts a `ticket_id` parameter but explicitly ignores it (ticket IDs no longer affect directory names). Its body is functionally equivalent to `validate_short_name` -- both check the same 31-character limit via `validate_identifier`. The single call site at `src/cli/chunk.py:125` redundantly calls both validators on the same name. Replace the call site with `validate_short_name` only and delete `validate_combined_chunk_name`.

3. **Migrate callers off `src/task_utils.py` re-export shim** (163 lines): This module exists solely to re-export symbols from the `task` package and `external_refs` for backward compatibility. There are 26 import sites in `src/` (14 files) and 33 in `tests/` (12 files) that import from `task_utils` instead of directly from `task` or `external_refs`. Migrating these imports and deleting the shim eliminates an unnecessary indirection layer.

## Success Criteria

- The function `_start_task_chunk` no longer exists in `src/cli/chunk.py`. Grep for `_start_task_chunk[^s]` returns zero matches across the codebase.
- The function `validate_combined_chunk_name` no longer exists in `src/cli/utils.py`. All call sites that previously used it now use `validate_short_name` directly. Grep for `validate_combined_chunk_name` returns zero matches.
- The file `src/task_utils.py` is deleted. All imports that previously referenced `task_utils` now import directly from `task`, `task.config`, `task.artifact_ops`, `task.promote`, `task.external`, `task.friction`, `task.overlap`, `task.exceptions`, or `external_refs` as appropriate.
- No import of `task_utils` appears anywhere in `src/` or `tests/`. Grep for `from task_utils import|import task_utils` returns zero matches.
- All existing tests pass (`uv run pytest tests/`) with no regressions.
