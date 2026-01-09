# Implementation Plan

## Approach

This chunk extends the bidirectional relationship between chunks and subsystems. Currently:
- `SubsystemFrontmatter` (in `models.py`) has a `chunks` field with `ChunkRelationship` entries
- Chunk frontmatter is parsed as raw dicts in `chunks.py` without a Pydantic model
- `ve chunk complete` validates chunk readiness but doesn't check subsystem refs

We will:
1. **Rename `ve chunk complete` → `ve chunk validate`** to better reflect its purpose
2. Create a `SubsystemRelationship` model (inverse of `ChunkRelationship`)
3. Extend chunk validation to check subsystem reference existence
4. Add `ve subsystem validate` command for subsystem ref checking
5. Update `/chunk-complete` slash command and all documentation to use `ve chunk validate`
6. Update the chunk GOAL.md template with the new `subsystems` field

Following TDD per docs/trunk/TESTING_PHILOSOPHY.md: write failing tests first, then implement.

## Sequence

### Step 1: Rename `ve chunk complete` to `ve chunk validate`

Rename the CLI command and update all references:

**Code changes:**
- `src/ve.py`: Rename `@chunk.command() def complete(...)` to `@chunk.command() def validate(...)`
- `tests/test_chunk_complete.py` → rename to `tests/test_chunk_validate.py`, update all test references

**Documentation updates:**
- `README.md`: Update `ve chunk complete` → `ve chunk validate`
- `docs/trunk/SPEC.md`: Update command reference
- `src/templates/commands/chunk-complete.md`: Update step 4 to use `ve chunk validate`

Location: `src/ve.py`, `tests/test_chunk_validate.py`, `README.md`, `docs/trunk/SPEC.md`, `src/templates/commands/chunk-complete.md`

### Step 2: Create SubsystemRelationship model and tests

Write tests first in `tests/test_models.py`:
- Valid subsystem_id format passes (`0001-validation`)
- Invalid format fails (missing prefix, wrong separator)
- Valid relationship types ("implements", "uses")
- Invalid relationship type fails

Then add `SubsystemRelationship` to `src/models.py`:
```python
class SubsystemRelationship(BaseModel):
    subsystem_id: str  # format: {NNNN}-{short_name}
    relationship: Literal["implements", "uses"]
```

Use the existing `CHUNK_ID_PATTERN` regex (same format applies to subsystem IDs).

Location: `src/models.py`, `tests/test_models.py`

### Step 3: Add subsystems field to chunk frontmatter parsing

Currently `parse_chunk_frontmatter` returns `dict | None`. The `subsystems` field will be parsed as part of this dict.

Add method `Chunks.validate_subsystem_refs(chunk_id: str) -> list[str]` that:
- Gets chunk frontmatter
- For each entry in `subsystems`, validates format and checks if subsystem directory exists
- Returns list of error messages

Write tests in `tests/test_chunks.py`:
- Empty subsystems list returns no errors
- Valid subsystem reference returns no errors
- Invalid subsystem_id format returns error
- Non-existent subsystem reference returns error message

Location: `src/chunks.py`, `tests/test_chunks.py`

### Step 4: Extend `validate_chunk_complete` to check subsystem refs

Update `Chunks.validate_chunk_complete()` to also call `validate_subsystem_refs()` and include those errors in the result.

Update tests in `tests/test_chunk_validate.py`:
- Chunk with invalid subsystem ref fails validation
- Chunk with valid subsystem ref passes validation

Location: `src/chunks.py`, `tests/test_chunk_validate.py`

### Step 5: Add chunk reference validation to Subsystems class

Add method `Subsystems.validate_chunk_refs(subsystem_id: str) -> list[str]` that:
- Gets subsystem frontmatter
- For each entry in `chunks`, checks if chunk directory exists in `docs/chunks/`
- Returns list of error messages for non-existent chunks

Write tests in `tests/test_subsystems.py`:
- Empty chunks list returns no errors
- Valid chunk reference returns no errors
- Non-existent chunk reference returns error message

Location: `src/subsystems.py`, `tests/test_subsystems.py`

### Step 6: Add `ve subsystem validate` CLI command

Add validation command for subsystems:
- `ve subsystem validate <subsystem_id>` - validates subsystem frontmatter and chunk refs

Output format:
- On success: "Subsystem {id} validation passed" with exit code 0
- On failure: List of errors with exit code 1

Write CLI tests in `tests/test_subsystem_validate.py`:
- `ve subsystem validate` with valid subsystem passes
- `ve subsystem validate` with invalid chunk ref fails
- `ve subsystem validate` with non-existent subsystem fails

Location: `src/ve.py`, `tests/test_subsystem_validate.py`

### Step 7: Update chunk GOAL.md template

Add `subsystems` field to the chunk template frontmatter and document its usage in the template comments.

Update `src/templates/chunk/GOAL.md`:
```yaml
---
status: {{ status | default('IMPLEMENTING') }}
ticket: {{ ticket_id | default('null', true) }}
parent_chunk: null
code_paths: []
code_references: []
narrative: null
subsystems: []
---
```

Add documentation in the template comment block explaining:
- Format: `subsystems: [{subsystem_id: "0001-name", relationship: "implements|uses"}]`
- When to use "implements" vs "uses"

Location: `src/templates/chunk/GOAL.md`

### Step 8: Update code_paths in chunk GOAL.md

Update the chunk's GOAL.md frontmatter `code_paths` field with the files touched.

## Dependencies

- Chunks 0014-0017 (subsystem schemas, CLI scaffolding, template) should be complete, which they appear to be based on the existing `SubsystemFrontmatter` and `Subsystems` class.

## Risks and Open Questions

1. **Backward compatibility**: Existing chunks don't have a `subsystems` field. The validation should treat missing/empty `subsystems` as valid (no refs to check).

2. **Command rename impact**: The rename from `complete` to `validate` affects:
   - `/chunk-complete` slash command (step 4 reference)
   - README.md examples
   - SPEC.md documentation
   - Historical chunk documentation (leave as-is for archaeology)

3. **Circular validation**: When validating bidirectional refs, we validate one direction at a time (chunk→subsystem or subsystem→chunk), which avoids infinite loops.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->