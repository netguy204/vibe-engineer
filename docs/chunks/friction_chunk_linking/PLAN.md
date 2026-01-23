<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds bidirectional linking between chunks and friction log entries. The design from `docs/investigations/friction_log_artifact/OVERVIEW.md` specifies:

1. **Chunk frontmatter field**: `friction_entries` array with `entry_id` (e.g., "F001") and `scope` ("full" or "partial")
2. **Validation**: Ensure referenced friction entries exist in `docs/trunk/FRICTION.md`

The implementation follows existing patterns for chunk-to-artifact references:
- Similar to `investigation` and `narrative` fields in frontmatter
- Similar validation pattern to `validate_investigation_ref()` and `validate_narrative_ref()`
- Uses the existing `Friction` class to parse and validate entries

**Key patterns to follow:**
- Pydantic model for the frontmatter field (like `SubsystemRelationship`)
- Validation method in `Chunks` class that returns `list[str]` errors
- Integration with `validate_chunk_complete()` like other reference validations
- CLI tests following the established patterns in `test_chunk_validate.py`

**Test-driven approach**: Write failing tests first for:
1. Valid friction_entries passes validation
2. Invalid friction entry ID fails validation
3. Chunks without friction_entries pass validation (optional field)

## Subsystem Considerations

No relevant subsystems in `docs/subsystems/` for this chunk.

## Sequence

### Step 1: Write failing tests for friction entry validation

Create test class `TestFrictionEntryRefValidation` in `tests/test_chunk_validate.py` following the pattern of `TestInvestigationRefValidation`:

1. `test_chunk_with_valid_friction_entries_passes` - Chunk referencing existing friction entries passes
2. `test_chunk_with_invalid_friction_entry_fails` - Chunk referencing non-existent entry fails with error
3. `test_chunk_with_no_friction_entries_passes` - Chunk without friction_entries field passes (optional)
4. `test_chunk_with_partial_scope_passes` - Chunk with `scope: partial` passes validation

Create helper method `_write_frontmatter_with_friction_entries()` similar to `_write_frontmatter_with_investigation()`.

Location: `tests/test_chunk_validate.py`

### Step 2: Add FrictionEntryReference model

Add Pydantic model to `src/models.py`:

```python
class FrictionEntryReference(BaseModel):
    """Reference to a friction entry that a chunk addresses."""

    entry_id: str  # e.g., "F001"
    scope: Literal["full", "partial"] = "full"
```

Include field validators:
- `entry_id` must match pattern `F\d+` (F followed by digits)
- `scope` must be "full" or "partial"

Location: `src/models.py`

### Step 3: Add friction_entries to ChunkFrontmatter

Extend `ChunkFrontmatter` class in `src/models.py`:

```python
friction_entries: list[FrictionEntryReference] = []
```

Location: `src/models.py`

### Step 4: Implement validate_friction_entries_ref method

Add validation method to `Chunks` class in `src/chunks.py`:

```python
def validate_friction_entries_ref(self, chunk_id: str) -> list[str]:
    """Validate friction entry references in a chunk's frontmatter.

    Checks that each referenced friction entry ID exists in FRICTION.md.
    """
```

Implementation:
1. Parse chunk frontmatter
2. If `friction_entries` is empty, return `[]` (no errors)
3. Use `Friction` class to parse FRICTION.md entries
4. Check each referenced entry_id exists in parsed entries
5. Return list of error messages for missing entries

Location: `src/chunks.py`

### Step 5: Integrate validation into validate_chunk_complete

Add friction entry validation to `validate_chunk_complete()` method in `src/chunks.py`:

```python
# Validate friction entry references
friction_errors = validation_chunks.validate_friction_entries_ref(chunk_name_to_validate)
errors.extend(friction_errors)
```

Place this after narrative validation, following the established pattern.

Location: `src/chunks.py`

### Step 6: Update chunk GOAL.md template

Add `friction_entries` to the GOAL.md Jinja2 template frontmatter:

```yaml
friction_entries: []
```

Add documentation in the template comments explaining:
- Purpose: Links chunk to friction entries it addresses
- Format: `[{entry_id: "F001", scope: "full"}, ...]`
- When to populate: During `/chunk-create` when addressing known friction
- Validation: `ve chunk validate` checks entries exist

Location: `src/templates/chunk/GOAL.md.jinja2`

### Step 7: Run tests and verify

Run the full test suite to ensure:
1. New friction entry validation tests pass
2. Existing tests still pass (no regressions)
3. Template renders correctly

```bash
uv run pytest tests/test_chunk_validate.py -v
uv run pytest tests/test_models.py -v
uv run pytest tests/ -v
```

## Dependencies

- **`friction_template_and_cli` chunk**: Must be ACTIVE. Provides:
  - `docs/trunk/FRICTION.md` template
  - `src/friction.py#Friction` class with `parse_entries()` method
  - `src/models.py#FrictionFrontmatter` and related models

The `friction_template_and_cli` chunk is already ACTIVE, so this dependency is satisfied.

## Risks and Open Questions

1. **FRICTION.md might not exist**: If a chunk references friction entries but FRICTION.md doesn't exist, should validation:
   - Fail with an error? (consistent with investigation/narrative validation)
   - Pass with a warning? (friction log is optional)

   **Decision**: Fail with a clear error. If the chunk claims to address friction, the friction log should exist. This is consistent with how investigation and narrative validation works.

2. **Entry ID format validation**: Should we validate the entry_id format (e.g., `F\d+`) in the Pydantic model, or only check existence?

   **Decision**: Validate format in Pydantic model. This catches typos early (e.g., "f001" vs "F001") before hitting the filesystem.

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