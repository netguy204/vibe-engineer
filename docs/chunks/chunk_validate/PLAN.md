# Implementation Plan

## Approach

This command follows the established patterns in the ve CLI:

1. **CLI layer in `src/ve.py`**: Add `chunk complete` command using Click, following the pattern of `chunk overlap` and `chunk start`
2. **Business logic in `src/chunks.py`**: Add validation method using Pydantic models for structured error reporting
3. **Pydantic models in new `src/models.py`**: Define `CodeRange` and `CodeReference` models separate from CLI for reuse and testability

The command validates two things:
- Status field must be `IMPLEMENTING` or `ACTIVE`
- `code_references` field must conform to the Pydantic schema

Per DEC-001, this is a uvx-executable CLI command with no external dependencies beyond what's already in use.

Following TESTING_PHILOSOPHY.md, we write failing tests first, then implement to make them pass. Tests verify semantically meaningful properties tied to success criteria.

## Sequence

### Step 1: Define Pydantic models

Create `src/models.py` with Pydantic v2 models:

```python
from pydantic import BaseModel

class CodeRange(BaseModel):
    lines: str  # "N-M" or "N" format
    implements: str

class CodeReference(BaseModel):
    file: str
    ranges: list[CodeRange]
```

Add `pydantic` to dependencies in `src/ve.py` script metadata.

Location: `src/models.py`

### Step 2: Write failing tests for status validation

Create `tests/test_chunk_complete.py` with tests for:
- Command exists and shows help
- Accepts optional chunk_id (defaults to latest)
- Accepts `--project-dir` option
- Fails with non-zero exit when status is not `IMPLEMENTING` or `ACTIVE`
- Error message states current status and explains why blocked

Location: `tests/test_chunk_complete.py`

### Step 3: Write failing tests for code_references validation

Add tests for:
- Valid code_references passes validation
- Missing `file` field in reference produces error with field path
- Missing `lines` field in range produces error with field path
- Missing `implements` field in range produces error with field path
- Wrong type (int instead of string) produces error with field path
- Multiple errors are reported together
- Empty code_references list fails with error explaining at least one reference is required

Location: `tests/test_chunk_complete.py`

### Step 4: Write failing tests for success output

Add tests for:
- Successful validation prints confirmation message
- Exit code 0 on success

Location: `tests/test_chunk_complete.py`

### Step 5: Implement validation method in Chunks class

Add `validate_chunk_complete(chunk_id: str)` method to `Chunks` class that:
1. Resolves chunk_id (default to latest if None)
2. Parses frontmatter
3. Checks status is `IMPLEMENTING` or `ACTIVE`
4. Validates `code_references` against Pydantic models
5. Returns structured result with success/errors

Location: `src/chunks.py`

### Step 6: Implement CLI command

Add `chunk complete` command to `src/ve.py`:
- Optional `chunk_id` argument
- `--project-dir` option
- Calls `chunks.validate_chunk_complete()`
- Formats validation errors for agent consumption
- Exits with appropriate code

Location: `src/ve.py`

### Step 7: Verify all tests pass

Run `pytest tests/test_chunk_complete.py` and ensure all tests pass.

Location: Terminal

## Dependencies

- Pydantic v2 must be added to script dependencies in `src/ve.py`
- Existing `Chunks` class methods: `resolve_chunk_id()`, `parse_chunk_frontmatter()`, `get_latest_chunk()`

## Risks and Open Questions

- **Pydantic error formatting**: Pydantic v2's `ValidationError` has a different structure than v1. Need to verify the error output format is agent-friendly.
- **Empty code_references**: Resolved - empty list is invalid. Every completed chunk must have at least one code reference.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->