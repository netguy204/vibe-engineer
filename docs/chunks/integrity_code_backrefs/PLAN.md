# Implementation Plan

## Approach

Extend the existing `_validate_code_backreferences` method in `src/integrity.py` to track and report line numbers for broken backreferences. The current implementation uses regex pattern matching with `finditer()` but only captures the matched chunk/subsystem ID, not the position within the file.

Key changes:
1. **Track line numbers during scanning**: Iterate through file content line-by-line instead of using `finditer()` on the entire content, allowing us to track the line number for each match.
2. **Extend error messages**: Include line number in the error's source field (e.g., `src/foo.py:42`) and message.
3. **Add tests**: Verify that line numbers are correctly reported for broken backreferences.

Building on:
- Existing `_validate_code_backreferences` method in `src/integrity.py`
- Existing regex patterns `CHUNK_BACKREF_PATTERN` and `SUBSYSTEM_BACKREF_PATTERN` from `chunks.py`
- Existing test patterns in `tests/test_integrity.py`

Per `docs/trunk/TESTING_PHILOSOPHY.md`, tests will be written first (TDD approach).

## Sequence

### Step 1: Write failing tests for line number reporting

Add tests to `tests/test_integrity.py` that verify:
1. Error source includes line number (e.g., `src/test.py:3`)
2. Error message mentions the line number
3. Multiple errors in the same file report correct, distinct line numbers

These tests will fail initially since the current implementation doesn't track line numbers.

Location: tests/test_integrity.py

### Step 2: Modify _validate_code_backreferences to track line numbers

Refactor the method to:
1. Read file content and split into lines
2. Iterate through lines with `enumerate()` to track line numbers (1-indexed)
3. Apply regex patterns to each line instead of the entire content
4. Include line number in `IntegrityError` source field as `{file_path}:{line_number}`
5. Update error message to include "at line {N}"

The refactored approach:
```python
for line_num, line in enumerate(content.splitlines(), start=1):
    match = CHUNK_BACKREF_PATTERN.match(line)
    if match:
        chunk_id = match.group(1)
        chunk_refs_found += 1
        if chunk_id not in self._chunk_names:
            errors.append(IntegrityError(
                source=f"{rel_path}:{line_num}",
                target=f"docs/chunks/{chunk_id}",
                link_type="code→chunk",
                message=f"Code backreference to non-existent chunk '{chunk_id}' at line {line_num}",
            ))
```

Location: src/integrity.py

### Step 3: Run tests and verify

Run the test suite to verify:
1. Previously failing tests now pass
2. No regressions in existing tests
3. The actual `ve validate` command outputs line numbers

## Dependencies

- `integrity_validate` chunk must be complete (provides the base `_validate_code_backreferences` method)
- Already satisfied: chunk is ACTIVE

## Risks and Open Questions

- **Pattern matching mode change**: The `CHUNK_BACKREF_PATTERN` and `SUBSYSTEM_BACKREF_PATTERN` use `re.MULTILINE` flag for matching `^` at line start. When switching to line-by-line iteration, we need to ensure the patterns still match correctly on individual lines (they should, since `^` will match at the start of each line string).

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->