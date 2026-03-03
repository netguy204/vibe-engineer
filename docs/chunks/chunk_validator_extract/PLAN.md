<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extract chunk validation logic from `src/chunks.py` into a new `src/chunk_validation.py` module. This is a pure extraction refactor with no behavioral changes. The pattern follows what was done in the `chunks_decompose` chunk, which extracted `backreferences.py`, `consolidation.py`, and `cluster_analysis.py` from `chunks.py`.

**Strategy:**

1. Create a new `src/chunk_validation.py` module containing the extracted symbols
2. Update `src/chunks.py` to:
   - Import from `chunk_validation` module
   - Re-export `ValidationResult` and `plan_has_content` for backward compatibility
   - Replace the extracted methods with thin delegation wrappers
3. Preserve all existing public APIs so callers don't need changes

**Testing approach:**

Per TESTING_PHILOSOPHY.md, this is a refactor with no behavioral changes. Existing tests in `tests/test_chunk_validate.py`, `tests/test_chunk_validate_inject.py`, and `tests/test_artifact_manager_errors.py` already cover the validation logic. All tests must pass after the extraction, which verifies:
- Backward compatibility of imports (`from chunks import ValidationResult`, `from chunks import plan_has_content`)
- Method delegation works correctly
- All validation outcomes remain identical

No new tests are needed because this is purely structural - we're not adding or changing behavior.

## Sequence

### Step 1: Create src/chunk_validation.py with extracted symbols

Create a new module `src/chunk_validation.py` containing:

1. **Imports** - Copy necessary imports from `chunks.py`:
   - `from __future__ import annotations`
   - `from dataclasses import dataclass, field`
   - `import pathlib`
   - `import re`
   - `from models import ChunkStatus`
   - `from symbols import parse_reference, extract_symbols, qualify_ref`

2. **ValidationResult dataclass** (lines 63-71 of chunks.py):
   ```python
   @dataclass
   class ValidationResult:
       """Result of chunk completion validation."""
       success: bool
       errors: list[str] = field(default_factory=list)
       warnings: list[str] = field(default_factory=list)
       chunk_name: str | None = None
   ```

3. **plan_has_content function** (lines 1359-1402 of chunks.py):
   Module-level function that checks if PLAN.md has actual content beyond template.

4. **_validate_symbol_exists function** (lines 960-994 of chunks.py):
   Validates that a symbolic reference points to an existing symbol. This is a helper used by `validate_chunk_complete`.

5. **_validate_symbol_exists_with_context function** (lines 997-1092 of chunks.py):
   Validates a symbolic reference with task context for cross-project refs.

6. **validate_chunk_complete function** (lines 802-957 of chunks.py):
   The main validation function. Needs access to the Chunks instance for resolution helpers (`resolve_chunk_location`, `parse_chunk_frontmatter_with_errors`, `validate_subsystem_refs`, etc.). Will be a standalone function that takes a Chunks instance as its first parameter.

7. **validate_chunk_injectable function** (lines 1284-1354 of chunks.py):
   Injection-time validation. Also needs Chunks instance. Will be a standalone function.

Add module-level backreference comment:
```python
# Chunk: docs/chunks/chunk_validator_extract - Chunk validation logic extraction
```

Location: `src/chunk_validation.py`

### Step 2: Update src/chunks.py to import and re-export

Modify `src/chunks.py`:

1. Add import at top (after existing imports):
   ```python
   from chunk_validation import (
       ValidationResult,
       plan_has_content,
       validate_chunk_complete as _validate_chunk_complete,
       validate_chunk_injectable as _validate_chunk_injectable,
       _validate_symbol_exists,
       _validate_symbol_exists_with_context,
   )
   ```

2. Remove the `ValidationResult` dataclass definition (lines 62-71)

3. Remove the `plan_has_content` function (lines 1357-1402)

4. Remove `_validate_symbol_exists` method (lines 959-994)

5. Remove `_validate_symbol_exists_with_context` method (lines 996-1092)

6. Replace `validate_chunk_complete` method with thin delegation wrapper:
   ```python
   def validate_chunk_complete(
       self,
       chunk_id: str | None = None,
       task_dir: pathlib.Path | None = None,
   ) -> ValidationResult:
       """Validate that a chunk is ready for completion.

       Delegates to chunk_validation.validate_chunk_complete().
       """
       return _validate_chunk_complete(self, chunk_id, task_dir)
   ```

7. Replace `validate_chunk_injectable` method with thin delegation wrapper:
   ```python
   def validate_chunk_injectable(self, chunk_id: str) -> ValidationResult:
       """Validate that a chunk is ready for injection.

       Delegates to chunk_validation.validate_chunk_injectable().
       """
       return _validate_chunk_injectable(self, chunk_id)
   ```

Location: `src/chunks.py`

### Step 3: Refactor extracted functions to work standalone

In `src/chunk_validation.py`, update the extracted functions:

1. `validate_chunk_complete(chunks: Chunks, chunk_id: str | None, task_dir: pathlib.Path | None)`:
   - Add `chunks` parameter as first argument (TYPE_CHECKING import for Chunks)
   - Replace all `self.` calls with `chunks.` calls
   - Replace calls to `self._validate_symbol_exists_with_context(...)` with direct calls to the module function

2. `validate_chunk_injectable(chunks: Chunks, chunk_id: str)`:
   - Add `chunks` parameter as first argument
   - Replace all `self.` calls with `chunks.` calls
   - Replace `plan_has_content(plan_path)` call to module function (already at module level)

3. `_validate_symbol_exists(project_dir: pathlib.Path, ref: str)`:
   - Add `project_dir` parameter (previously accessed via `self.project_dir`)
   - Update internal references to use parameter

4. `_validate_symbol_exists_with_context(project_dir: pathlib.Path, ref: str, task_dir: pathlib.Path | None, chunk_project: pathlib.Path | None)`:
   - Add `project_dir` parameter
   - Update internal references to use parameters

Add TYPE_CHECKING import for Chunks to avoid circular import:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chunks import Chunks
```

Location: `src/chunk_validation.py`

### Step 4: Verify backward compatibility exports

Ensure `src/chunks.py` re-exports the extracted symbols at module level so existing imports work:

1. `ValidationResult` - already re-exported via import
2. `plan_has_content` - already re-exported via import

Check that these imports work:
- `from chunks import ValidationResult` (used in tests)
- `from chunks import plan_has_content` (used in `src/orchestrator/api.py`)
- `chunks.validate_chunk_complete()` (used in `src/cli/chunk.py`)
- `chunks.validate_chunk_injectable()` (used in `src/cli/chunk.py`)

Location: `src/chunks.py`

### Step 5: Run tests and verify no regressions

Run the test suite to verify:

1. All existing tests pass:
   ```bash
   uv run pytest tests/test_chunk_validate.py tests/test_chunk_validate_inject.py tests/test_artifact_manager_errors.py -v
   ```

2. Run full test suite to catch any import issues:
   ```bash
   uv run pytest tests/ -v
   ```

3. Verify the line count reduction in `src/chunks.py`:
   - Original: ~1471 lines
   - Expected reduction: ~200-250 lines (ValidationResult + plan_has_content + validate_chunk_complete + validate_chunk_injectable + _validate_symbol_exists + _validate_symbol_exists_with_context)
   - Target: ~1220-1270 lines

Location: Tests and verification

## Dependencies

This chunk depends on:
- **models_subpackage** (declared in GOAL.md frontmatter): The models subpackage must be complete so that imports like `from models import ChunkStatus` resolve correctly from the new `chunk_validation.py` module.

## Risks and Open Questions

1. **Circular import risk**: The `validate_chunk_complete` function needs access to the `Chunks` class for resolution methods (`resolve_chunk_location`, `parse_chunk_frontmatter_with_errors`, etc.). Using `TYPE_CHECKING` guard for the Chunks import should avoid circular imports, but verify at runtime.

2. **Internal method access**: The extracted functions call internal helpers on the Chunks instance:
   - `_validate_symbol_exists_with_context` - now a module function
   - `_parse_frontmatter_from_content` - remains on Chunks class
   - `validate_subsystem_refs`, `validate_investigation_ref`, `validate_narrative_ref`, `validate_friction_entries_ref` - remain on Chunks class

   The module functions will need to call back into the chunks instance for these, which may feel slightly awkward but maintains the existing method contracts.

3. **Test import patterns**: Some tests import `from chunks import plan_has_content` directly. Ensure the re-export is at module level so these continue to work.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->