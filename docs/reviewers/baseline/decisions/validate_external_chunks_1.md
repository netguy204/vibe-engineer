---
decision: APPROVE
summary: 'APPROVE: Make `ve validate` handle external chunks correctly by detecting
  them and skipping validation (since they''re validated in their home repository)'
operator_review: good
---

## Assessment

The implementation comprehensively addresses the problem of `ve validate` failing on repositories with external chunks:

**1. External chunk detection** ✓
- `_build_artifact_index()` uses `is_external_artifact()` from `external_refs.py` to detect external chunks
- External chunks are stored in `_external_chunk_names` set, separate from `_chunk_names`
- Only local chunks (`_chunk_names`) are iterated during validation

**2. IntegrityResult tracking** ✓
- Added `external_chunks_skipped: int = 0` field to `IntegrityResult` dataclass
- Populated at end of `validate()`: `external_chunks_skipped=len(self._external_chunk_names)`

**3. CLI verbose output** ✓
- Lines 179-180 in `ve.py`: Shows "External chunks skipped: N" when `--verbose` flag is used and count > 0

**4. Code backreference handling** ✓
- Code backreferences to external chunks are valid (the directory exists locally with `external.yaml`)
- Implementation checks both `_chunk_names` and `_external_chunk_names` for code→chunk validation
- Bidirectional check skipped for external chunks (no GOAL.md with code_references to compare against)

**5. Test coverage** ✓
- 6 new tests in `TestIntegrityValidatorExternalChunks` class:
  - `test_project_with_only_external_chunks_passes`
  - `test_mixed_local_and_external_chunks`
  - `test_external_chunks_skipped_count_reported`
  - `test_local_chunk_with_error_still_fails_with_external_present`
  - `test_cli_verbose_shows_external_chunks_skipped`
  - `test_code_backref_to_external_chunk_passes`
- All 50 integrity tests pass

**6. Live verification** ✓
- `ve validate` on the actual codebase now succeeds (exit code 0) with `xr_ve_worktrees_flag` external chunk present
- Shows "External chunks skipped: 1" in verbose output

**Code backreferences** ✓
- Present in `src/integrity.py` (line 4)
- Present in `src/ve.py` (line 155)

## Decision Rationale

All four success criteria from GOAL.md are satisfied:
1. ✅ `ve validate` succeeds when the chunks directory contains external chunks
2. ✅ External chunks are clearly identified in validation output ("External chunks skipped: N")
3. ✅ Local chunks continue to be validated as before (all pre-existing tests pass)
4. ✅ Tests cover both external and local chunk validation scenarios (6 new tests)

The implementation follows the PLAN.md approach exactly: detect external chunks during index build, skip them during validation, track the skip count, and report in verbose output. The design decision to skip rather than dereference is well-justified per DEC-006.

## Context

- Goal: Make `ve validate` handle external chunks correctly by detecting them and skipping validation (since they're validated in their home repository)
- Linked artifacts: subsystems: workflow_artifacts (uses), cross_repo_operations (uses)
