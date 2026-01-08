---
status: ACTIVE
---

# Implementation Plan

## Approach

The implementation extends the existing `Chunks` class and `start` command in `src/ve.py`. Key changes:

1. Reverse argument order and make `ticket_id` optional (Click argument configuration)
2. Add validation functions that collect all errors before failing
3. Normalize inputs to lowercase after validation
4. Add duplicate detection with user prompt via `click.confirm()`
5. Add `--yes` flag to skip prompts for scripting/CI
6. Add success output

Per DEC-001, this remains a uvx-based CLI with no additional dependencies beyond Click and Jinja2.

## Sequence

### Step 1: Set up test infrastructure

Create `tests/test_ve.py` with pytest. Test the current behavior as a baseline before modifying.

**Files:**
- Create: `tests/test_ve.py`

### Step 2: Fix argument order and make ticket_id optional

Change `start` command signature from `(ticket_id, short_name)` to `(short_name, ticket_id=None)`.

**Files:**
- Modify: `src/ve.py:70-77`
- Test: `tests/test_ve.py`

**Test first:** Command accepts `short_name` alone and with `ticket_id`.

### Step 3: Implement short_name validation

Add `validate_short_name()` function that collects all errors:
- Rejects spaces
- Rejects characters outside `[a-zA-Z0-9_-]`
- Rejects length >= 32

**Files:**
- Modify: `src/ve.py`
- Test: `tests/test_ve.py`

**Test first:** Each validation rule fails with appropriate message.

### Step 4: Implement ticket_id validation

Add `validate_ticket_id()` function with same character rules as short_name.

**Files:**
- Modify: `src/ve.py`
- Test: `tests/test_ve.py`

**Test first:** Invalid ticket_id rejected with message.

### Step 5: Implement lowercase normalization

Normalize `short_name` and `ticket_id` to lowercase after validation passes.

**Files:**
- Modify: `src/ve.py`
- Test: `tests/test_ve.py`

**Test first:** `My_Feature` becomes `my_feature`, `VE-001` becomes `ve-001`.

### Step 6: Implement duplicate detection with prompt

Add check in `Chunks.create_chunk()` for existing chunks with same short_name + ticket_id combo. Use `click.confirm()` to prompt user.

**Files:**
- Modify: `src/ve.py`
- Test: `tests/test_ve.py`

**Test first:** Duplicate detected, prompt shown, abort on "no".

### Step 7: Add --yes flag to skip prompts

Add `--yes` option to `start` command that bypasses confirmation prompts.

**Files:**
- Modify: `src/ve.py`
- Test: `tests/test_ve.py`

**Test first:** With `--yes`, duplicate creation proceeds without prompt.

### Step 8: Handle path format for omitted ticket_id

Modify `Chunks.create_chunk()` to use `{NNNN}-{short_name}` format when ticket_id is None.

**Files:**
- Modify: `src/ve.py:42`
- Test: `tests/test_ve.py`

**Test first:** Chunk created without ticket has correct path format.

### Step 9: Add success output

Print the created path after successful chunk creation.

**Files:**
- Modify: `src/ve.py:77`
- Test: `tests/test_ve.py`

**Test first:** Output matches expected format `Created docs/chunks/...`.

## Dependencies

- pytest (run via `uvx pytest`)

## Risks and Open Questions

None remaining - all questions resolved during planning.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->