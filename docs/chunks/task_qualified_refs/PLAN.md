<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extends `SymbolicReference` and `parse_reference` to support project-qualified paths in the format `org/repo::path#symbol`. The approach builds on existing code:

1. **Extend `parse_reference`** in `src/symbols.py` to return a 3-tuple `(project, file_path, symbol_path)` instead of the current 2-tuple. The `::` delimiter separates the project qualifier from the file path.

2. **Update all call sites** of `parse_reference` to handle the new return type. Call sites in `src/chunks.py` and `src/subsystems.py` will pass `current_project=None` (local context) to maintain backward compatibility.

3. **Extend `is_parent_of`** to compare fully-qualified references. When both references have the same project (including both `None`), the existing hierarchical comparison applies. References from different projects never overlap.

4. **Extend `SymbolicReference` validation** in `src/models.py` to accept the `org/repo::path` format, reusing `_require_valid_repo_ref` for the project qualifier validation.

5. **Follow TDD** per `docs/trunk/TESTING_PHILOSOPHY.md`: Write failing tests first, then implementation.

This aligns with DEC-002 (git not assumed) by enabling references to span multiple repositories in a task context.

## Subsystem Considerations

No subsystems are directly relevant to this chunk. The `template_system` and `workflow_artifacts` subsystems documented in `docs/subsystems/` are not touched by this work, which focuses on the symbol parsing and reference validation layer.

## Sequence

### Step 1: Write failing tests for `parse_reference` with project qualification

Add tests to `tests/test_symbols.py` that verify:
- `parse_reference("acme/proj::src/foo.py")` returns `("acme/proj", "src/foo.py", None)`
- `parse_reference("acme/proj::src/foo.py#Bar")` returns `("acme/proj", "src/foo.py", "Bar")`
- `parse_reference("acme/proj::src/foo.py#Bar::baz")` returns `("acme/proj", "src/foo.py", "Bar::baz")`
- `parse_reference("src/foo.py#Bar")` returns `(None, "src/foo.py", "Bar")` (backward compatible)
- `parse_reference("src/foo.py#Bar", current_project="acme/proj")` returns `("acme/proj", "src/foo.py", "Bar")`

Also test error cases:
- Multiple `::` delimiters should be invalid
- Empty project qualifier (`::src/foo.py`) should be invalid

Location: `tests/test_symbols.py`

### Step 2: Implement extended `parse_reference`

Update `parse_reference` in `src/symbols.py` to:
- Accept optional `current_project: str | None` parameter
- Return 3-tuple `(project, file_path, symbol_path)`
- Parse `::` delimiter for project qualification
- Use `current_project` when no explicit qualifier present

Location: `src/symbols.py`

### Step 3: Write failing tests for `is_parent_of` with project context

Add tests to verify:
- Same project + hierarchical relationship → True
- Different projects + same file path → False (never overlap across projects)
- Both None projects + hierarchical relationship → True (backward compatible)
- `is_parent_of("acme/proj::src/foo.py#Bar", "acme/proj::src/foo.py#Bar::baz")` → True
- `is_parent_of("acme/a::src/foo.py#Bar", "acme/b::src/foo.py#Bar")` → False

Location: `tests/test_symbols.py`

### Step 4: Extend `is_parent_of` for project-qualified references

Update `is_parent_of` in `src/symbols.py` to:
- Accept optional `current_project: str | None` parameter
- Parse both references with project context
- Return False immediately if projects differ
- Apply existing hierarchical logic when projects match

Location: `src/symbols.py`

### Step 5: Write failing tests for `SymbolicReference` with project qualification

Add tests to `tests/test_models.py` that verify:
- `SymbolicReference(ref="acme/proj::src/foo.py#Bar", implements="...")` validates successfully
- `SymbolicReference(ref="acme/proj::src/foo.py", implements="...")` validates (file-only)
- Invalid formats are rejected: `"::src/foo.py"`, `"acme::::src/foo.py"`, `"acme/proj::src/foo.py#Bar#baz"`
- Backward compatible: `SymbolicReference(ref="src/foo.py#Bar", implements="...")` still works

Location: `tests/test_models.py`

### Step 6: Extend `SymbolicReference.validate_ref` for project qualification

Update the `validate_ref` validator in `src/models.py` to:
- Check for at most one `::` delimiter
- If `::` present, validate project portion using `_require_valid_repo_ref`
- Validate file path and symbol portions with existing rules
- Maintain backward compatibility for non-qualified references

Location: `src/models.py`

### Step 7: Update call sites of `parse_reference`

Update all call sites to handle the new 3-tuple return:
- `src/chunks.py`: `_validate_symbol_exists`, `find_overlapping_chunks`
- `src/subsystems.py`: `_find_overlapping_refs`

Pass `current_project=None` to maintain local behavior. The tuple unpacking changes from `(file_path, symbol_path)` to `(_, file_path, symbol_path)` where the project is ignored in local context.

Locations: `src/chunks.py`, `src/subsystems.py`

### Step 8: Write integration tests for overlap detection across projects

Add tests verifying:
- Two refs from same project correctly detect overlap
- Two refs from different projects never overlap, even with identical file+symbol
- Mixed qualified and unqualified refs (with `current_project`) detect overlap correctly

Location: `tests/test_symbols.py` or `tests/test_chunks.py`

### Step 9: Run full test suite and fix any regressions

Execute `uv run pytest tests/` and address any failures. Verify backward compatibility for all existing tests.

## Dependencies

No external dependencies. This builds on existing validation utilities (`_require_valid_repo_ref` in `src/models.py`) and the current `parse_reference` / `is_parent_of` functions in `src/symbols.py`.

## Risks and Open Questions

1. **Breaking change to `parse_reference` return type**: Changing from 2-tuple to 3-tuple is a breaking change. All call sites must be updated simultaneously. The plan handles this in Step 7.

2. **Validation strictness for project qualifier**: The goal says to validate via `_require_valid_repo_ref`, but that function raises `ValueError` on invalid input. Need to decide whether `parse_reference` should raise or return an error indicator. Current approach: `parse_reference` does not validate—it just parses. Validation happens in `SymbolicReference.validate_ref`.

3. **Edge case: `::` in file paths**: Windows paths don't use `::`, and Unix paths never contain it, so this delimiter choice is safe. No risk identified.

## Deviations

<!-- Populated during implementation -->