<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk follows the established pattern in `models.py` for workflow artifact types.
The existing implementations of `SubsystemStatus`/`SubsystemFrontmatter`,
`InvestigationStatus`/`InvestigationFrontmatter`, and `NarrativeStatus`/`NarrativeFrontmatter`
serve as templates.

**Strategy:**
1. Add `ChunkStatus` StrEnum to `models.py` following the pattern of other status enums
2. Add `ChunkFrontmatter` Pydantic model to `models.py` following the pattern of other
   frontmatter models
3. Update `chunks.py` to return `ChunkFrontmatter | None` from `parse_chunk_frontmatter()`
4. Update all call sites in `chunks.py` to use typed attribute access
5. Update call sites in other files (`ve.py`, `task_utils.py`) that read chunk frontmatter

**Testing approach per TESTING_PHILOSOPHY.md:**
- ChunkStatus enum: No tests needed (trivial, tests Python's StrEnum)
- ChunkFrontmatter validation: Add tests that verify rejection of invalid input
- parse_chunk_frontmatter changes: Update existing tests to use typed access

## Subsystem Considerations

- **docs/subsystems/0002-workflow_artifacts** (DOCUMENTED): This chunk IMPLEMENTS the
  subsystem by adding `ChunkStatus` StrEnum and `ChunkFrontmatter` Pydantic model,
  resolving the "Chunk Status Not a StrEnum" deviation.

The subsystem is DOCUMENTED status, but this chunk's explicit goal is to resolve a
documented deviation, so this is expected work.

## Sequence

### Step 1: Add ChunkStatus StrEnum to models.py

Add the `ChunkStatus` StrEnum after the existing status enums (around line 40, after
`InvestigationStatus`). Include all five status values from the GOAL.md template comments:

```python
class ChunkStatus(StrEnum):
    """Status values for chunk lifecycle."""

    FUTURE = "FUTURE"  # Queued for future work, not yet being implemented
    IMPLEMENTING = "IMPLEMENTING"  # Currently being implemented
    ACTIVE = "ACTIVE"  # Accurately describes current or recently-merged work
    SUPERSEDED = "SUPERSEDED"  # Another chunk has modified the code this chunk governed
    HISTORICAL = "HISTORICAL"  # Significant drift; kept for archaeology only
```

Add chunk backreference comment.

Location: `src/models.py`

### Step 2: Add ChunkFrontmatter Pydantic model to models.py

Add `ChunkFrontmatter` after the other frontmatter models (at end of file, after
`InvestigationFrontmatter`). Fields based on the GOAL.md template:

```python
class ChunkFrontmatter(BaseModel):
    """Frontmatter schema for chunk GOAL.md files.

    Validates the YAML frontmatter in chunk documentation.
    """

    status: ChunkStatus
    ticket: str | None = None
    parent_chunk: str | None = None
    code_paths: list[str] = []
    code_references: list[SymbolicReference] = []
    narrative: str | None = None
    subsystems: list[SubsystemRelationship] = []
    proposed_chunks: list[ProposedChunk] = []
    dependents: list[ExternalChunkRef] = []  # For cross-repo chunks
```

Add chunk backreference comment.

Location: `src/models.py`

### Step 3: Audit and migrate existing chunk frontmatter

Before tightening validation, ensure all existing chunks in this repo have valid frontmatter:

1. Run a script or manual check to find chunks with:
   - Lowercase status values (e.g., `status: active` should be `status: ACTIVE`)
   - Missing required fields
   - Invalid field values

2. Fix any issues found by updating the GOAL.md files directly.

3. Verify by attempting to parse all chunks with the new `ChunkFrontmatter` model.

This ensures we don't break the repo's own chunks when we tighten validation.

Location: `docs/chunks/*/GOAL.md`

### Step 4: Write tests for ChunkFrontmatter validation

Add tests to `tests/test_models.py` for `ChunkFrontmatter` validation behavior:

1. `test_invalid_status_value_rejected` - Invalid status string fails
2. `test_missing_status_rejected` - Missing status field fails
3. `test_valid_frontmatter_parses_successfully` - Valid frontmatter with all fields works
4. `test_optional_fields_default_correctly` - ticket, parent_chunk, narrative default to None;
   lists default to empty

Follow the pattern established by `TestInvestigationFrontmatter`.

Location: `tests/test_models.py`

### Step 5: Update parse_chunk_frontmatter return type and implementation

Change `parse_chunk_frontmatter()` in `chunks.py` to:
- Return `ChunkFrontmatter | None` instead of `dict | None`
- Import `ChunkFrontmatter` and `ChunkStatus` from models
- Use `ChunkFrontmatter.model_validate()` for parsing
- Catch `ValidationError` from pydantic and return `None`

The pattern matches `parse_narrative_frontmatter()` and `parse_investigation_frontmatter()`.

Location: `src/chunks.py`

### Step 6: Update call sites in chunks.py

Update all methods that call `parse_chunk_frontmatter()` to use typed access:

1. `get_current_chunk()` (line 110-111):
   - Change `frontmatter.get("status") == "IMPLEMENTING"` to
   - `frontmatter.status == ChunkStatus.IMPLEMENTING`

2. `activate_chunk()` (line 148-149):
   - Change `frontmatter.get("status")` to `frontmatter.status`
   - Change string comparison to enum comparison

3. `find_overlapping_chunks()` (line 333, 369):
   - Change `frontmatter.get("code_references", [])` to `frontmatter.code_references`
   - Change `fm.get("status") != "ACTIVE"` to `fm.status != ChunkStatus.ACTIVE`

4. `validate_chunk_complete()` (line 459, 467):
   - Change `frontmatter.get("status")` to `frontmatter.status`
   - Change `frontmatter.get("code_references", [])` to `frontmatter.code_references`
   - Update valid_statuses check to use enum values

5. `validate_subsystem_refs()` (line 638):
   - Change `frontmatter.get("subsystems", [])` to `frontmatter.subsystems`
   - Note: The subsystems field returns `list[SubsystemRelationship]`, so the loop
     needs to access `.subsystem_id` and `.relationship` attributes instead of dict access

Location: `src/chunks.py`

### Step 7: Update call sites in ve.py and task_utils.py

Update external call sites that use `parse_chunk_frontmatter()`:

1. `ve.py` line 192:
   - Change `frontmatter.get("status", "UNKNOWN")` to handle the typed model
   - The status is now an enum, so display `frontmatter.status.value` if needed

2. `task_utils.py` lines 396-397:
   - Change `frontmatter.get("status", "UNKNOWN")` to `frontmatter.status.value if frontmatter else "UNKNOWN"`
   - Change `frontmatter.get("dependents", [])` to `frontmatter.dependents if frontmatter else []`

Location: `src/ve.py`, `src/task_utils.py`

### Step 8: Update existing tests in test_chunks.py

Update tests that check frontmatter directly to use typed access:

1. `TestParseFrontmatterDependents.test_parse_frontmatter_with_dependents`:
   - Change `assert "dependents" in frontmatter` to check `frontmatter.dependents`
   - Update assertions to use model attribute access

2. `TestParseFrontmatterDependents.test_parse_frontmatter_without_dependents`:
   - Change `assert "dependents" not in frontmatter` to `assert frontmatter.dependents == []`
   - Change `frontmatter.get("status")` to `frontmatter.status.value`

These tests may need to write YAML that conforms to ChunkFrontmatter validation (valid status values).

Location: `tests/test_chunks.py`

### Step 9: Run tests and fix any issues

Run `uv run pytest tests/` to verify all tests pass. Fix any issues that arise from
the type changes.

### Step 10: Update code_paths in GOAL.md

Update the chunk's GOAL.md frontmatter with the actual files modified:
- src/models.py
- src/chunks.py
- src/ve.py
- src/task_utils.py
- tests/test_models.py
- tests/test_chunks.py

Location: `docs/chunks/0036-chunk_frontmatter_model/GOAL.md`

## Risks and Open Questions

1. **Backward compatibility for malformed frontmatter**: Currently `parse_chunk_frontmatter()`
   returns an empty dict for malformed frontmatter. With validation, it will return `None`.
   This should be fine since callers already handle `None`, but need to verify.

2. **Existing chunks in this repo**: Step 3 addresses this by auditing and migrating any
   chunks with malformed frontmatter (e.g., lowercase status values) before tightening validation.

3. **Test fixtures with minimal frontmatter**: Some test fixtures write chunks with minimal
   YAML (just status). The new model requires `status` to be a valid `ChunkStatus` value.
   Tests that write `status: active` (lowercase) will fail - need to use `status: ACTIVE`.

4. **The dependents field**: The existing `ChunkDependent` model has a `dependents` field
   with `list[ExternalChunkRef]`. The new `ChunkFrontmatter` should include this for
   cross-repo support. Need to verify this is correctly handled.

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
-->