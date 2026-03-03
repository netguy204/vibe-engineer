<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds `_with_errors` variants to the ArtifactManager base class and all
artifact frontmatter parsers to provide consistent error surfacing across all workflow
artifact types.

**Strategy:**

1. **Add `parse_frontmatter_with_errors()` to ArtifactManager** - The base class already
   has `parse_frontmatter()` that uses the shared `frontmatter.parse_frontmatter()`. Add
   a parallel `parse_frontmatter_with_errors()` method that uses
   `frontmatter.parse_frontmatter_with_errors()` instead.

2. **Add convenience methods to concrete managers** - Each artifact manager (Narratives,
   Investigations, Subsystems) already has `parse_{type}_frontmatter()` as an alias for
   `parse_frontmatter()`. Add corresponding `parse_{type}_frontmatter_with_errors()`
   aliases for consistency and backward compatibility with the Chunks class pattern.

3. **Fix `plan_has_content()` exception handling** - Replace the bare `except Exception`
   with specific exception handling for expected errors (`FileNotFoundError`,
   `PermissionError`), allowing unexpected errors to propagate.

4. **Document the convention** - Add code comments explaining when to use `_with_errors`
   variants (validation commands, error reporting) vs. regular parsers (silent failure
   acceptable).

**Building on existing code:**

- `frontmatter.py` already provides the core `parse_frontmatter_with_errors()` function
  that returns `tuple[T | None, list[str]]`
- `chunks.py` already has `parse_chunk_frontmatter_with_errors()` as the reference pattern
- `artifact_manager.py` provides the base class that all managers inherit from

**Test strategy:**

Per TESTING_PHILOSOPHY.md, tests should assert semantically meaningful properties:
- Error variants return descriptive error messages for common failure modes
- Error messages contain actionable information (field names, expected formats)
- Regular parsers still work (backward compatibility)

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS error surfacing
  for the ArtifactManager pattern. The workflow_artifacts subsystem already documents
  the manager class pattern (`parse_{type}_frontmatter()` interface). This chunk extends
  that pattern with `_with_errors` variants.

## Sequence

### Step 1: Add `parse_frontmatter_with_errors()` to ArtifactManager

Add a new method to `ArtifactManager` base class that delegates to the shared
`frontmatter.parse_frontmatter_with_errors()`:

```python
def parse_frontmatter_with_errors(
    self, artifact_id: str
) -> tuple[FrontmatterT | None, list[str]]:
    """Parse and validate frontmatter with detailed error messages.

    Args:
        artifact_id: The artifact directory name.

    Returns:
        Tuple of (frontmatter, errors) where:
        - frontmatter is the validated model if successful, None otherwise
        - errors is a list of error messages (empty if parsing succeeded)
    """
    from frontmatter import parse_frontmatter_with_errors

    main_path = self.get_main_file_path(artifact_id)
    if not main_path.exists():
        return None, [f"{self.artifact_type_name} '{artifact_id}' not found"]

    return parse_frontmatter_with_errors(main_path, self.frontmatter_model_class)
```

Add backreference: `# Chunk: docs/chunks/validation_error_surface - Error surfacing for frontmatter parsing`

Location: `src/artifact_manager.py`

### Step 2: Add `parse_narrative_frontmatter_with_errors()` to Narratives

The Narratives class has special handling for the legacy 'chunks' field that maps to
'proposed_chunks'. The `parse_narrative_frontmatter()` method overrides the base class
to handle this. Add a corresponding `_with_errors` variant:

```python
def parse_narrative_frontmatter_with_errors(
    self, narrative_id: str
) -> tuple[NarrativeFrontmatter | None, list[str]]:
    """Parse OVERVIEW.md frontmatter with error details.

    Handles legacy 'chunks' field mapping to 'proposed_chunks'.

    Args:
        narrative_id: The narrative directory name.

    Returns:
        Tuple of (frontmatter, errors).
    """
    from frontmatter import extract_frontmatter_dict

    overview_path = self.narratives_dir / narrative_id / "OVERVIEW.md"
    if not overview_path.exists():
        return None, [f"Narrative '{narrative_id}' not found"]

    frontmatter_data = extract_frontmatter_dict(overview_path)
    if frontmatter_data is None:
        return None, [f"Could not parse frontmatter in {overview_path}"]

    try:
        # Handle legacy 'chunks' field by mapping to 'proposed_chunks'
        if "chunks" in frontmatter_data and "proposed_chunks" not in frontmatter_data:
            frontmatter_data["proposed_chunks"] = frontmatter_data.pop("chunks")
        return NarrativeFrontmatter.model_validate(frontmatter_data), []
    except ValidationError as e:
        errors = []
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"{loc}: {msg}")
        return None, errors
```

Location: `src/narratives.py`

### Step 3: Add `parse_investigation_frontmatter_with_errors()` to Investigations

Investigations doesn't have special legacy field handling, so it can simply delegate
to the base class method:

```python
def parse_investigation_frontmatter_with_errors(
    self, investigation_id: str
) -> tuple[InvestigationFrontmatter | None, list[str]]:
    """Parse OVERVIEW.md frontmatter with error details.

    This is an alias for parse_frontmatter_with_errors() that maintains the
    original method name for backward compatibility and consistency with
    parse_investigation_frontmatter().

    Args:
        investigation_id: The investigation directory name.

    Returns:
        Tuple of (frontmatter, errors).
    """
    return self.parse_frontmatter_with_errors(investigation_id)
```

Location: `src/investigations.py`

### Step 4: Add `parse_subsystem_frontmatter_with_errors()` to Subsystems

Same pattern as investigations - delegate to base class:

```python
def parse_subsystem_frontmatter_with_errors(
    self, subsystem_id: str
) -> tuple[SubsystemFrontmatter | None, list[str]]:
    """Parse OVERVIEW.md frontmatter with error details.

    This is an alias for parse_frontmatter_with_errors() that maintains the
    original method name for backward compatibility and consistency with
    parse_subsystem_frontmatter().

    Args:
        subsystem_id: The subsystem directory name.

    Returns:
        Tuple of (frontmatter, errors).
    """
    return self.parse_frontmatter_with_errors(subsystem_id)
```

Location: `src/subsystems.py`

### Step 5: Fix `plan_has_content()` exception handling

Replace the bare `except Exception` with specific exception handling:

```python
def plan_has_content(plan_path: pathlib.Path) -> bool:
    """Check if PLAN.md has actual content beyond the template.

    Looks for content in the '## Approach' section that isn't just the
    template's HTML comment block.

    Args:
        plan_path: Path to the PLAN.md file

    Returns:
        True if the plan has actual content, False if:
        - File doesn't exist
        - File cannot be read due to permissions
        - File is just a template without content

    Note:
        Other exceptions (e.g., encoding errors) will propagate to the caller.
    """
    try:
        content = plan_path.read_text()
    except FileNotFoundError:
        return False
    except PermissionError:
        return False

    # ... rest of the function unchanged
```

Add backreference: `# Chunk: docs/chunks/validation_error_surface - Specific exception handling`

Location: `src/chunks.py` around line 1472

### Step 6: Add documentation comments

Add a comment block near the imports or at the module level in `artifact_manager.py`
explaining the error surfacing convention:

```python
# ERROR SURFACING CONVENTION:
#
# All artifact frontmatter parsers provide two variants:
#
# 1. parse_frontmatter(artifact_id) -> Frontmatter | None
#    - Returns None on any failure (file not found, parse error, validation error)
#    - Use when silent failure is acceptable (e.g., checking if artifact exists)
#
# 2. parse_frontmatter_with_errors(artifact_id) -> tuple[Frontmatter | None, list[str]]
#    - Returns (None, errors) with descriptive messages on failure
#    - Use when caller needs to report errors (validation commands, CLI feedback)
#
# Concrete managers provide aliases (parse_{type}_frontmatter_with_errors) for
# consistency with the existing parse_{type}_frontmatter() naming pattern.
```

### Step 7: Write tests for error surfacing

Add tests to verify the new `_with_errors` methods work correctly:

**Test file**: `tests/test_artifact_manager_errors.py`

Tests to write:
1. `test_parse_frontmatter_with_errors_returns_errors_for_missing_artifact` - verify
   error message mentions artifact name
2. `test_parse_frontmatter_with_errors_returns_errors_for_invalid_yaml` - verify
   YAML error is reported
3. `test_parse_frontmatter_with_errors_returns_field_errors_for_validation_failure` -
   verify Pydantic field errors are formatted with field names
4. `test_parse_frontmatter_with_errors_returns_empty_errors_on_success` - verify
   successful parse returns (model, [])

For narrative-specific tests (legacy 'chunks' field handling):
5. `test_narrative_with_errors_handles_legacy_chunks_field` - verify legacy field
   still works with error surfacing

For `plan_has_content`:
6. `test_plan_has_content_returns_false_for_missing_file` - specific FileNotFoundError
7. `test_plan_has_content_propagates_unexpected_errors` - verify non-handled errors
   propagate (can test with a mock or by creating a broken symlink)

### Step 8: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter to include the files being modified:

```yaml
code_paths:
  - src/artifact_manager.py
  - src/narratives.py
  - src/investigations.py
  - src/subsystems.py
  - src/chunks.py
  - tests/test_artifact_manager_errors.py
```

### Step 9: Run tests and verify

Run the test suite to ensure:
- New tests pass
- Existing tests still pass (backward compatibility)
- No regressions in artifact parsing

```bash
uv run pytest tests/test_artifact_manager_errors.py tests/test_frontmatter.py -v
uv run pytest tests/ -v  # Full suite
```

## Dependencies

This chunk depends on:
- **frontmatter_io** - The shared frontmatter I/O utilities that provide
  `parse_frontmatter_with_errors()` and `parse_frontmatter_from_content_with_errors()`
- **artifact_manager_base** - The ArtifactManager base class that will be extended
  with the new method

Both dependencies are already complete (referenced in chunk frontmatter `depends_on`).

## Risks and Open Questions

1. **Narrative legacy field handling** - The Narratives class has special handling for
   mapping 'chunks' to 'proposed_chunks'. The `_with_errors` variant needs to replicate
   this logic rather than delegating to the base class. This is handled in Step 2.

2. **Exception handling in `plan_has_content`** - The current bare `except Exception`
   may be intentionally catching something specific. Review the call sites to understand
   the expected behavior. Call sites are `orchestrator/api.py` and `chunks.py` itself
   for validation. Both expect a boolean return - they should handle missing files
   gracefully but propagate other errors.

3. **Import cycle risk** - Adding `ValidationError` import to narratives.py. This
   should be fine as it's a Pydantic import, not a local module import.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->