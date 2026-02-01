<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The core implementation for validating `proposed_chunks[].chunk_directory` references was
completed as part of the `integrity_validate` chunk (docs/chunks/integrity_validate). The
validation logic exists in `src/integrity.py`:

- `_validate_narrative_chunk_refs()` - Validates narrative proposed_chunks (lines 259-295)
- `_validate_investigation_chunk_refs()` - Validates investigation proposed_chunks (lines 297-333)
- `_validate_friction_chunk_refs()` - Validates friction log proposed_chunks (lines 357-391)

**Gap identified:** While the implementation is complete, test coverage is incomplete. The
`tests/test_integrity.py` file has tests for narrative→chunk and investigation→chunk
validation in `TestIntegrityValidatorProposedChunks`, but **no explicit tests for friction→chunk
proposed_chunks validation**.

This chunk will:
1. Verify the existing implementation meets all success criteria
2. Add missing test coverage for friction→chunk proposed_chunks validation
3. Ensure error messages properly identify the parent artifact and broken reference

## Subsystem Considerations

No subsystems are directly relevant. This chunk adds test coverage to an existing validation
module without touching subsystem patterns.

## Sequence

### Step 1: Verify existing implementation coverage

Confirm that `_validate_friction_chunk_refs()` in `src/integrity.py` properly:
- Detects stale chunk_directory references (references to non-existent chunks)
- Detects malformed references (with `docs/chunks/` prefix)
- Skips null/missing chunk_directory (chunk not yet created)
- Returns appropriate `IntegrityError` with source, target, link_type, and message

Location: `src/integrity.py` lines 357-391

**Verification:** Code review confirms the implementation matches the narrative and
investigation validation patterns.

### Step 2: Add friction→chunk proposed_chunks validation tests

Add test cases to `tests/test_integrity.py` within `TestIntegrityValidatorProposedChunks`:

1. `test_friction_valid_chunk_directory_passes` - Friction log with valid chunk_directory
   references passes validation
2. `test_friction_invalid_chunk_directory_fails` - Friction log with stale chunk_directory
   reference fails with appropriate error
3. `test_friction_null_chunk_directory_passes` - Friction log with null chunk_directory
   (chunk not yet created) passes validation
4. `test_friction_malformed_chunk_directory_detected` - Friction log with `docs/chunks/`
   prefix is detected as malformed

Each test should:
- Use the existing `write_friction_log` helper (lines 163-202)
- Assert on `result.success`, `len(result.errors)`, and error message content
- Verify `link_type == "friction→chunk"` for friction-specific errors

Location: `tests/test_integrity.py`

### Step 3: Verify error message format

Confirm error messages from friction validation identify:
- The parent artifact: `"docs/trunk/FRICTION.md"`
- The broken chunk reference: `"docs/chunks/{chunk_name}"`
- The link type: `"friction→chunk"`
- A human-readable message describing the issue

This is verified through the new tests in Step 2.

## Dependencies

- **integrity_validate** (docs/chunks/integrity_validate) - ACTIVE
  - Provides `IntegrityValidator` class with `_validate_friction_chunk_refs()` method
  - Provides test helpers in `tests/test_integrity.py`

## Risks and Open Questions

- **Low risk:** The implementation is already complete. Only test coverage needs to be added.
- The `write_friction_log` helper already supports `proposed_chunks`, so no new test
  infrastructure is needed.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->