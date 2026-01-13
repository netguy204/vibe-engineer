<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The core change is to filter artifacts by status when computing tips in
`ArtifactIndex._build_index_for_type()`. Currently, tips are computed as
"artifacts not referenced in any other artifact's `created_after`"—this needs
to become "ACTIVE/IMPLEMENTING artifacts not referenced by other
ACTIVE/IMPLEMENTING artifacts."

**Strategy:**

1. Add a `_parse_status()` helper function (similar to `_parse_created_after()`)
   to extract the status field from artifact frontmatter.

2. Define which statuses are "tip-eligible" per artifact type:
   - **Chunks**: `ACTIVE`, `IMPLEMENTING` (excludes FUTURE, SUPERSEDED, HISTORICAL)
   - **Narratives**: `ACTIVE` (excludes DRAFTING, COMPLETED)
   - **Investigations**: No filtering (all statuses considered—ONGOING is active,
     others are terminal)
   - **Subsystems**: No filtering (all non-DEPRECATED statuses represent active
     documentation)

3. Modify `_build_index_for_type()` to:
   - Parse status from each artifact's frontmatter
   - Filter to only tip-eligible artifacts when computing tips
   - Keep the full ordered list unchanged (status filtering only affects tips)

4. Bump `_INDEX_VERSION` to force cache invalidation.

**Testing strategy (TDD):**

- Write failing tests first that verify the new filtering behavior
- Tests will create chunks with different statuses and verify `find_tips()`
  only returns ACTIVE/IMPLEMENTING chunks
- Similar tests for narratives
- Verify investigations/subsystems remain unchanged

**Files to modify:**
- `src/artifact_ordering.py`: Core logic changes
- `tests/test_artifact_ordering.py`: New tests for status-filtered tips

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS
  enhanced tip detection logic for the artifact ordering system. The subsystem's
  `ArtifactIndex` code reference lists `find_tips` as the method being enhanced.
  Since the subsystem is in REFACTORING status, any improvements to this code
  should follow the established patterns.

## Sequence

### Step 1: Write failing tests for chunk status filtering

Create tests in `tests/test_artifact_ordering.py` that verify:

1. `find_tips()` for chunks returns only ACTIVE or IMPLEMENTING chunks
2. FUTURE chunks are excluded from tips even if they have no dependents
3. Multiple FUTURE chunks created after the same tip all get the same `created_after`
   (simulated by checking that only the IMPLEMENTING tip is returned)
4. SUPERSEDED and HISTORICAL chunks are also excluded from tips

These tests will fail initially because the current implementation doesn't filter
by status.

Location: `tests/test_artifact_ordering.py`

### Step 2: Write failing tests for narrative status filtering

Create tests that verify:

1. `find_tips()` for narratives returns only ACTIVE narratives
2. DRAFTING narratives are excluded from tips
3. COMPLETED narratives are excluded from tips

Location: `tests/test_artifact_ordering.py`

### Step 3: Write tests confirming no filtering for investigations/subsystems

Create tests that verify:

1. `find_tips()` for investigations returns all investigations regardless of status
2. `find_tips()` for subsystems returns all subsystems regardless of status

These tests should pass with the current implementation (no change expected).

Location: `tests/test_artifact_ordering.py`

### Step 4: Add `_parse_status()` helper function

Create a helper function similar to `_parse_created_after()` that extracts the
`status` field from an artifact's frontmatter.

```python
def _parse_status(file_path: Path) -> str | None:
    """Parse the status field from a file's frontmatter.

    Returns the status string or None if not found/invalid.
    """
```

Location: `src/artifact_ordering.py`

### Step 5: Define tip-eligible statuses per artifact type

Add a constant mapping artifact types to their tip-eligible statuses:

```python
_TIP_ELIGIBLE_STATUSES: dict[ArtifactType, set[str] | None] = {
    ArtifactType.CHUNK: {"ACTIVE", "IMPLEMENTING"},
    ArtifactType.NARRATIVE: {"ACTIVE"},
    ArtifactType.INVESTIGATION: None,  # No filtering
    ArtifactType.SUBSYSTEM: None,  # No filtering
}
```

Using `None` to indicate "no filtering" is cleaner than listing all statuses.

Location: `src/artifact_ordering.py`

### Step 6: Modify `_build_index_for_type()` to filter tips by status

Update the method to:

1. Parse status for each artifact along with created_after
2. Store statuses in a dict for lookup
3. When computing tips, filter to only include artifacts with tip-eligible statuses

The ordered list remains unchanged—status filtering only affects tip computation.

Location: `src/artifact_ordering.py#_build_index_for_type`

### Step 7: Bump `_INDEX_VERSION`

Increment `_INDEX_VERSION` from 2 to 3 to invalidate cached indexes that don't
have status-aware tip detection.

Location: `src/artifact_ordering.py`

### Step 8: Run all tests and verify

Run `uv run pytest tests/test_artifact_ordering.py -v` to verify:
- All new tests pass
- All existing tests still pass
- No regressions in ordering behavior

### Step 9: Update chunk backreferences

Add backreference comment to the modified `_build_index_for_type` method:

```python
# Chunk: docs/chunks/ordering_active_only - Status-aware tip filtering
```

Location: `src/artifact_ordering.py`

## Dependencies

None. This chunk builds on the existing `ArtifactIndex` infrastructure from
`artifact_ordering_index` and `artifact_index_no_git` chunks. All required
status enums (`ChunkStatus`, `NarrativeStatus`, etc.) already exist in `models.py`.

## Risks and Open Questions

1. **Should status changes trigger index rebuild?** Currently the index only
   rebuilds when directories are added/removed, not when content changes. If a
   chunk's status changes from IMPLEMENTING to ACTIVE, the tips remain correct
   (both are tip-eligible). However, if status changes from IMPLEMENTING to
   SUPERSEDED, the index will have stale tips until next rebuild.

   **Resolution:** Accept this. Status changes that affect tip eligibility are
   rare (chunk completion is typically followed by creating new work). Users can
   call `rebuild()` explicitly if needed. Adding content-based staleness detection
   would significantly increase complexity and slow down the common case.

2. **What about artifacts with missing/invalid status?** If an artifact has no
   status field or an unrecognized status value, should it be included in tips?

   **Resolution:** Exclude artifacts with missing/invalid status from tips when
   filtering is enabled for that type. This is conservative—better to exclude
   potentially problematic artifacts than to include them as tips. The
   `_parse_status()` function will return `None` for missing/invalid status.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->