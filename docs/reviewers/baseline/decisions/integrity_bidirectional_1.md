---
decision: APPROVE
summary: 'APPROVE: Add warnings for bidirectional consistency violations between chunks
  and their parent artifacts (narratives/investigations) and between code backreferences
  and chunk code_references'
operator_review: good
---

## Assessment

The implementation comprehensively addresses all success criteria:

**1. Chunk↔Narrative bidirectional check** ✓
- `_validate_chunk_outbound()` lines 278-289 check if narrative's proposed_chunks includes the chunk
- Emits `IntegrityWarning` with `link_type="chunk↔narrative"` when asymmetric
- Test: `test_chunk_narrative_bidirectional_warning`, `test_chunk_narrative_bidirectional_valid`

**2. Chunk↔Investigation bidirectional check** ✓
- `_validate_chunk_outbound()` lines 302-313 check if investigation's proposed_chunks includes the chunk
- Emits `IntegrityWarning` with `link_type="chunk↔investigation"` when asymmetric
- Test: `test_chunk_investigation_bidirectional_warning`, `test_chunk_investigation_bidirectional_valid`

**3. Code↔Chunk bidirectional check** ✓
- `_validate_code_backreferences()` lines 538-550 check if chunk's code_references includes the file
- Matches on file path only (not symbol), as per PLAN.md Risk #3
- Emits `IntegrityWarning` with `link_type="code↔chunk"` when asymmetric
- Tests: `test_code_chunk_bidirectional_warning`, `test_code_chunk_bidirectional_valid`, `test_code_chunk_bidirectional_matches_file_path_only`

**4. Warnings distinguishable from errors** ✓
- CLI uses "Warning:" prefix vs "Error:" prefix (line 194 in `ve.py`)
- Exit code 0 for warnings-only, 1 for errors
- Live test confirmed: `ve validate` shows 27 warnings with exit 0

**5. --strict flag promotes warnings to errors** ✓
- CLI `--strict` flag (lines 158-159 in `ve.py`) adds warning count to error count
- Live test confirmed: `ve validate --strict` exits with code 1 and shows 28 errors

**6. Test coverage** ✓
- 8 tests in `TestIntegrityValidatorBidirectional` class covering all scenarios
- All 44 integrity tests pass
- 2104 total tests pass (1 pre-existing unrelated failure)

**Architecture alignment:**
- Uses reverse indexes (`_narrative_chunks`, `_investigation_chunks`, `_chunk_code_files`) built during `validate()` per PLAN.md Steps 2, 5
- Follows existing patterns from `integrity_validate`, `integrity_code_backrefs`, `integrity_proposed_chunks`
- `IntegrityWarning` dataclass already existed per dependency chunks

## Decision Rationale

All six success criteria from GOAL.md are satisfied:
1. ✅ `ve validate` warns when chunk→narrative link lacks corresponding narrative→chunk link
2. ✅ `ve validate` warns when chunk→investigation link lacks corresponding investigation→chunk link
3. ✅ `ve validate` warns when code→chunk backref lacks corresponding chunk→code reference
4. ✅ Warnings are distinguishable from errors (different prefix, exit code 0 vs 1)
5. ✅ `ve validate --strict` flag promotes warnings to errors
6. ✅ Tests cover bidirectional consistency detection (8 tests in dedicated class)

The implementation follows the PLAN.md sequence exactly and addresses all design decisions documented there. No deviations noted.

## Context

- Goal: Add warnings for bidirectional consistency violations between chunks and their parent artifacts (narratives/investigations) and between code backreferences and chunk code_references
- Linked artifacts: investigation: referential_integrity; depends_on: integrity_validate, integrity_code_backrefs, integrity_proposed_chunks
