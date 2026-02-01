---
decision: APPROVE
summary: 'APPROVE: Validate that `proposed_chunks[].chunk_directory` references in
  narratives, investigations, and friction log point to existing chunks'
operator_review: good
---

## Assessment

The implementation is complete and properly addresses all success criteria. Review findings:

**1. Core Implementation in `src/integrity.py`:**
- `_validate_narrative_chunk_refs()` (lines 259-295): Validates narrative proposed_chunks
- `_validate_investigation_chunk_refs()` (lines 297-333): Validates investigation proposed_chunks
- `_validate_friction_chunk_refs()` (lines 357-391): Validates friction log proposed_chunks

All three methods follow the same pattern:
- Parse frontmatter to extract proposed_chunks
- For each proposed_chunk with a non-null chunk_directory:
  - Detect malformed references (with `docs/chunks/` prefix)
  - Verify the chunk exists in the project
  - Return appropriate `IntegrityError` with source, target, link_type, and message

**2. Test Coverage in `tests/test_integrity.py` (32 tests total):**

The `TestIntegrityValidatorProposedChunks` class includes complete friction→chunk validation tests:
- `test_friction_valid_chunk_directory_passes` - Valid reference passes (line 454)
- `test_friction_invalid_chunk_directory_fails` - Stale reference fails with correct error (line 472)
- `test_friction_null_chunk_directory_passes` - Null/missing passes (line 490)
- `test_friction_malformed_chunk_directory_detected` - Malformed prefix detected (line 503)

**3. Error Messages:**

All error messages properly identify:
- Source file: `"docs/trunk/FRICTION.md"` (or narrative/investigation path)
- Target reference: `"docs/chunks/{chunk_name}"`
- Link type: `"friction→chunk"`, `"narrative→chunk"`, or `"investigation→chunk"`
- Human-readable message describing the issue

**4. Live Validation:**

Running `ve validate` successfully detected real malformed references in the investigation's proposed_chunks (they had `docs/chunks/` prefixes). This confirms the validation works correctly.

## Decision Rationale

All five success criteria from GOAL.md are satisfied:

1. ✅ `ve validate` detects stale `chunk_directory` references in narrative OVERVIEW.md files - Implemented in `_validate_narrative_chunk_refs()`
2. ✅ `ve validate` detects stale `chunk_directory` references in investigation OVERVIEW.md files - Implemented in `_validate_investigation_chunk_refs()`
3. ✅ `ve validate` detects stale `chunk_directory` references in FRICTION.md - Implemented in `_validate_friction_chunk_refs()`
4. ✅ Error messages identify the parent artifact and the broken chunk reference - All errors include source, target, link_type, and descriptive message
5. ✅ Tests cover detection of stale proposed_chunks references - 4 friction-specific tests + narrative/investigation tests

The implementation follows the existing validation patterns from `integrity_validate` and adds the test coverage that was identified as missing in the PLAN.md. All 32 integrity tests pass.

## Context

- Goal: Validate that `proposed_chunks[].chunk_directory` references in narratives, investigations, and friction log point to existing chunks
- Linked artifacts: investigation: referential_integrity, depends_on: integrity_validate
