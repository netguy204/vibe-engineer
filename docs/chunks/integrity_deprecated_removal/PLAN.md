<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a straightforward dead code removal task. The four deprecated standalone validation functions in `src/integrity.py` were introduced in the `integrity_deprecate_standalone` chunk as backward-compatibility shims. They emit deprecation warnings and delegate to `Chunks` class methods, which in turn route through `IntegrityValidator`. No production code calls these shims—the migration is complete.

The removal strategy is surgical deletion:
1. Remove the four deprecated functions from `src/integrity.py`
2. Remove the `import warnings` statement (only used by the deprecated functions)
3. Remove the `TestDeprecatedStandaloneFunctions` test class from `tests/test_integrity.py`
4. Update backreference comments in `src/chunks.py` that incorrectly reference the deleted functions
5. Verify no imports remain elsewhere and all tests pass

No new tests are required—we are deleting dead code and its tests, not adding functionality.

## Sequence

### Step 1: Delete the four deprecated functions from src/integrity.py

Remove lines 772-914 containing:
- `validate_chunk_subsystem_refs` (lines 772-801)
- `validate_chunk_investigation_ref` (lines 803-839)
- `validate_chunk_narrative_ref` (lines 841-876)
- `validate_chunk_friction_entries_ref` (lines 878-914)

Also remove the preceding backreference comments for each function.

Location: `src/integrity.py`

### Step 2: Remove the `import warnings` statement from src/integrity.py

The `import warnings` on line 19 is only used by the deprecated functions' `warnings.warn()` calls. Other uses of `warnings` in the file are a local variable name (collecting validation warnings), not the Python warnings module.

Location: `src/integrity.py`, line 19

### Step 3: Delete the TestDeprecatedStandaloneFunctions test class

Remove the entire test class from `tests/test_integrity.py`:
- `TestDeprecatedStandaloneFunctions` (lines 1338-1445)
- Contains 5 test methods testing deprecation warning emission and backward compatibility

Location: `tests/test_integrity.py`

### Step 4: Update backreference comments in src/chunks.py

The `Chunks` class methods (`validate_subsystem_refs`, `validate_investigation_ref`, `validate_narrative_ref`, `validate_friction_entries_ref`) contain backreference comments stating they delegate to `integrity.validate_chunk_*`. These comments are now incorrect—the methods route through `IntegrityValidator`, not through the deleted standalone functions.

Update or remove these outdated comments:
- Line 916: `# Chunk: docs/chunks/chunks_decompose - Thin wrapper delegating to integrity.validate_chunk_subsystem_refs`
- Line 939: `# Chunk: docs/chunks/chunks_decompose - Thin wrapper delegating to integrity.validate_chunk_investigation_ref`
- Line 962: `# Chunk: docs/chunks/chunks_decompose - Thin wrapper delegating to integrity.validate_chunk_narrative_ref`
- Line 984: `# Chunk: docs/chunks/chunks_decompose - Thin wrapper delegating to integrity.validate_chunk_friction_entries_ref`

These should be updated to reflect that the methods now route through `IntegrityValidator.validate_chunk()`.

Location: `src/chunks.py`

### Step 5: Verify no remaining imports of the deleted functions

Grep the non-worktree source and test files for any remaining imports or references to:
- `validate_chunk_subsystem_refs`
- `validate_chunk_investigation_ref`
- `validate_chunk_narrative_ref`
- `validate_chunk_friction_entries_ref`

Exclude documentation files (GOAL.md, PLAN.md, reviewer notes) from this check as they describe the deletion itself.

### Step 6: Run tests to verify no regressions

Run the full test suite to ensure:
- No tests import the deleted functions
- No tests fail due to missing exports
- The `IntegrityValidator` path continues to work correctly

Command: `uv run pytest tests/`

## Risks and Open Questions

- **Low risk**: The deleted functions are explicitly deprecated with clear migration paths. The test that verified they "still return correct errors" confirms the replacement path (`IntegrityValidator.validate_chunk`) works.

- **Documentation files**: Several docs/chunks and docs/reviewers files reference these functions. These references are historical documentation, not code, and do not need modification. They provide archaeology showing why the deprecated functions existed and when they were removed.
