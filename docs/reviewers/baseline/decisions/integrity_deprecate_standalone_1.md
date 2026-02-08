---
decision: APPROVE
summary: All success criteria satisfied - four standalone validation functions deprecated with warnings, callers route through IntegrityValidator, no duplicate Chunks() instantiation, behavior preserved, all 136 tests pass
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: The four standalone validation functions (`validate_chunk_subsystem_refs`, `validate_chunk_investigation_ref`, `validate_chunk_narrative_ref`, `validate_chunk_friction_entries_ref`) are removed or clearly deprecated

- **Status**: satisfied
- **Evidence**: All four functions in `src/integrity.py` (lines 770-912) now emit `DeprecationWarning` via `warnings.warn()` with stacklevel=2, including clear guidance to use `Chunks.validate_*()` or `IntegrityValidator.validate_chunk()`. Each function has `.. deprecated::` docstring notation.

### Criterion 2: All callers of these functions route through `IntegrityValidator` or a shared implementation

- **Status**: satisfied
- **Evidence**:
  - The deprecated standalone functions delegate to `Chunks.validate_*()` methods (e.g., line 798-799: `chunk_mgr = Chunks(project_dir); return chunk_mgr.validate_subsystem_refs(chunk_id)`)
  - The `Chunks` wrapper methods (lines 899-985 in `chunks.py`) route through `IntegrityValidator.validate_chunk()` and filter by `link_type`
  - No production code imports the deprecated standalone functions (only test code testing the deprecation warnings)

### Criterion 3: No duplicate `Chunks()` instantiation for validation purposes

- **Status**: satisfied
- **Evidence**:
  - The `Chunks.validate_*()` methods construct `Project` and `IntegrityValidator` once per validation call (lines 910-916 in chunks.py)
  - `IntegrityValidator` accesses the `Chunks` instance via `self._project.chunks` (line 116 in integrity.py)
  - The deprecated standalone functions delegate to `Chunks` methods which use the unified code path

### Criterion 4: Validation behavior is preserved — same errors and warnings are produced

- **Status**: satisfied
- **Evidence**:
  - The `_errors_to_messages()` helper (lines 726-762 in integrity.py) converts `IntegrityError` objects to the same string format used by the original standalone functions
  - Test `test_deprecated_function_still_returns_correct_errors` (lines 1425-1445 in test_integrity.py) verifies deprecated functions return correct errors
  - The existing `TestValidateSubsystemRefs` test class in test_chunks.py passes with the new implementation

### Criterion 5: All integrity and validation tests pass

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/test_integrity.py tests/test_chunks.py -v` shows all 136 tests pass (65 in test_integrity.py, 71 in test_chunks.py). This includes:
  - `TestDeprecatedStandaloneFunctions` (5 tests) verifying deprecation warnings
  - `TestIntegrityValidatorSingleChunk` (4 tests) verifying the new `validate_chunk()` method
  - `TestValidateSubsystemRefs` (8 tests) verifying the Chunks wrapper methods

## Feedback Items

<!-- Not applicable - APPROVE decision -->

## Escalation Reason

<!-- Not applicable - APPROVE decision -->
