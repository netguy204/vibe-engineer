---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/chunk_validation.py
  - src/chunks.py
code_references:
  - ref: src/chunk_validation.py
    implements: "New module containing extracted validation logic - ValidationResult, plan_has_content, validate_chunk_complete, validate_chunk_injectable, _validate_symbol_exists, _validate_symbol_exists_with_context"
  - ref: src/chunk_validation.py#ValidationResult
    implements: "Structured error reporting dataclass for validation outcomes"
  - ref: src/chunk_validation.py#plan_has_content
    implements: "Checks if PLAN.md has actual content beyond template"
  - ref: src/chunk_validation.py#_validate_symbol_exists
    implements: "Validates that a symbolic reference points to an existing symbol"
  - ref: src/chunk_validation.py#_validate_symbol_exists_with_context
    implements: "Cross-project code reference validation via task context"
  - ref: src/chunk_validation.py#validate_chunk_complete
    implements: "Main validation function for chunk completion - status, code_references, subsystem/investigation/narrative/friction refs"
  - ref: src/chunk_validation.py#validate_chunk_injectable
    implements: "Injection-time validation for orchestrator - status-content consistency"
  - ref: src/chunks.py#Chunks::validate_chunk_complete
    implements: "Thin delegation wrapper preserving public API"
  - ref: src/chunks.py#Chunks::validate_chunk_injectable
    implements: "Thin delegation wrapper preserving public API"
narrative: arch_decompose
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- models_subpackage
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

Extract chunk validation logic from `src/chunks.py` (1489 lines) into a new `src/chunk_validation.py` module. The Chunks class has accumulated validation methods that are conceptually distinct from core chunk management (creation, listing, resolution, status transitions). By moving validation into its own module, the Chunks class shrinks significantly and each module has a single, clear responsibility.

The following symbols move to `src/chunk_validation.py`:

- `ValidationResult` dataclass (structured error reporting for validation outcomes)
- `validate_chunk_complete()` (~150 lines, the largest validation method -- checks status, code_references, subsystem/investigation/narrative/friction refs)
- `validate_chunk_injectable()` (orchestrator injection-time validation -- checks status-content consistency with PLAN.md)
- `_validate_symbol_exists()` (verifies symbolic code references point to existing symbols)
- `_validate_symbol_exists_with_context()` (cross-project code reference validation via task context)
- `plan_has_content()` (module-level function detecting populated vs template-only PLAN.md)

The Chunks class retains thin delegation methods that call the extracted module, preserving the existing public API (`chunks.validate_chunk_complete(...)`, `chunks.validate_chunk_injectable(...)`). All callers in `src/cli/chunk.py` and `src/orchestrator/api.py` continue to work without import changes. The `plan_has_content` function, which is imported directly by `src/orchestrator/api.py`, is re-exported from `src/chunks.py` for backward compatibility.

## Success Criteria

- A new `src/chunk_validation.py` module exists containing `ValidationResult`, `validate_chunk_complete()`, `validate_chunk_injectable()`, `_validate_symbol_exists()`, `_validate_symbol_exists_with_context()`, and `plan_has_content()`
- The `Chunks` class in `src/chunks.py` delegates `validate_chunk_complete` and `validate_chunk_injectable` to the extracted module via thin wrapper methods, preserving the existing method signatures
- `src/chunks.py` re-exports `ValidationResult` and `plan_has_content` so that existing callers (`from chunks import ValidationResult`, `from chunks import plan_has_content`) continue to work without modification
- `src/cli/chunk.py` calls `chunks.validate_chunk_complete()` and `chunks.validate_chunk_injectable()` with no import changes required
- `src/orchestrator/api.py` imports `plan_has_content` from `chunks` with no changes required
- No behavioral changes: all validation logic produces identical results (same errors, same warnings, same success/failure outcomes)
- All existing tests pass, including `tests/test_chunk_validate_inject.py` and `tests/test_artifact_manager_errors.py` (which test `plan_has_content` exception handling)
- `src/chunks.py` line count is reduced by approximately 200-250 lines (the extracted validation methods plus `ValidationResult` and `plan_has_content`)

