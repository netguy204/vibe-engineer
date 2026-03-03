<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The four standalone validation functions in `src/integrity.py` (lines 705-913) duplicate the validation logic already present in `IntegrityValidator._validate_chunk_outbound()`:

| Standalone Function | IntegrityValidator Method |
|---------------------|---------------------------|
| `validate_chunk_subsystem_refs()` | `_validate_chunk_outbound()` → subsystem validation block (lines 399-421) |
| `validate_chunk_investigation_ref()` | `_validate_chunk_outbound()` → investigation validation block (lines 374-395) |
| `validate_chunk_narrative_ref()` | `_validate_chunk_outbound()` → narrative validation block (lines 350-371) |
| `validate_chunk_friction_entries_ref()` | `_validate_chunk_outbound()` → friction entries validation block (lines 424-434) |

The key differences:
1. **Return type**: Standalone functions return `list[str]` (error messages), while `IntegrityValidator` returns `IntegrityError` objects
2. **Instantiation**: Standalone functions optionally create a new `Chunks()` instance if not provided; `IntegrityValidator` accesses managers via `Project`
3. **Bidirectional checks**: `IntegrityValidator` includes bidirectional consistency warnings; standalone functions do not

**Strategy**: Rather than maintaining two code paths, the `Chunks` wrapper methods will call through to `IntegrityValidator` with a focused scope. We'll add a method `IntegrityValidator.validate_chunk_outbound(chunk_id)` that validates a single chunk and returns structured results that the `Chunks` wrappers can convert to `list[str]`.

This approach:
- Eliminates code duplication (DRY principle)
- Preserves the `Chunks` class API for backward compatibility
- Routes all validation through a single, well-tested code path
- The standalone functions are marked deprecated with `warnings.warn()` pointing callers to use `IntegrityValidator` or the `Chunks` wrapper methods

## Subsystem Considerations

- **docs/subsystems/friction_tracking**: The standalone function `validate_chunk_friction_entries_ref` has a subsystem backreference to friction_tracking. When deprecating this function, the routing through `IntegrityValidator` will preserve this relationship. No action needed beyond ensuring the deprecation warning guides users correctly.

## Sequence

### Step 1: Add public single-chunk validation method to IntegrityValidator

Add a new public method `validate_chunk(self, chunk_name: str) -> tuple[list[IntegrityError], list[IntegrityWarning]]` that:
1. Builds the artifact index (calls `_build_artifact_index()`)
2. Builds the bidirectional consistency indexes (calls `_build_parent_chunk_index()`)
3. Calls `_validate_chunk_outbound(chunk_name)` for the specified chunk
4. Returns errors and warnings

This provides a focused entry point for validating a single chunk without running the full project-wide validation.

**Location**: `src/integrity.py`, add method to `IntegrityValidator` class (around line 248, before `validate()`)

**Test**: Add test in `tests/test_integrity.py` to verify single-chunk validation works correctly.

### Step 2: Add helper to convert IntegrityError to string messages

Add a helper function `_errors_to_messages(errors: list[IntegrityError]) -> list[str]` that converts `IntegrityError` objects to the string format used by the existing standalone functions.

The format should match the current behavior: `"{target_type} '{target_name}' does not exist in docs/{artifact_type}/"`.

**Location**: `src/integrity.py`, module-level function near the standalone functions

### Step 3: Update Chunks wrapper methods to use IntegrityValidator

Modify the four wrapper methods in `Chunks` to route through `IntegrityValidator.validate_chunk()`:

```python
def validate_subsystem_refs(self, chunk_id: str) -> list[str]:
    """Validate subsystem references in a chunk's frontmatter."""
    from project import Project
    project = Project(self.project_dir)
    validator = IntegrityValidator(self.project_dir, project=project)
    errors, _ = validator.validate_chunk(chunk_id)
    # Filter to only subsystem-related errors
    return _errors_to_messages([e for e in errors if e.link_type == "chunk→subsystem"])
```

Apply similar pattern to:
- `validate_investigation_ref()` → filter `link_type == "chunk→investigation"`
- `validate_narrative_ref()` → filter `link_type == "chunk→narrative"`
- `validate_friction_entries_ref()` → filter `link_type == "chunk→friction"`

**Location**: `src/chunks.py`, methods around lines 902-961

**Note**: The `Chunks` wrapper methods now accept `self` (already have access to `self.project_dir`) and can construct a `Project` internally. The `ChunksProtocol` and the `chunks` parameter on standalone functions become unnecessary for the wrapper methods.

### Step 4: Add deprecation warnings to standalone functions

Mark the four standalone functions as deprecated using `warnings.warn()`:

```python
import warnings

def validate_chunk_subsystem_refs(
    project_dir: pathlib.Path,
    chunk_id: str,
    chunks: ChunksProtocol | None = None,
) -> list[str]:
    """Validate subsystem references in a chunk's frontmatter.

    .. deprecated::
        Use Chunks(project_dir).validate_subsystem_refs(chunk_id) or
        IntegrityValidator(project_dir).validate_chunk(chunk_id) instead.
    """
    warnings.warn(
        "validate_chunk_subsystem_refs is deprecated. Use Chunks.validate_subsystem_refs() "
        "or IntegrityValidator.validate_chunk() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Existing implementation continues to work for backward compatibility
    ...
```

Apply the same pattern to all four functions.

**Location**: `src/integrity.py`, lines 705-913

### Step 5: Remove redundant Chunks instantiation from standalone functions

The standalone functions currently create a new `Chunks()` instance when `chunks=None`. Since these functions are now deprecated and callers should use the `Chunks` wrapper methods or `IntegrityValidator` directly, we can simplify the deprecated functions to:
1. Keep the function signature for backward compatibility
2. Emit deprecation warning
3. Delegate to the new unified code path via `Chunks` class methods

```python
def validate_chunk_subsystem_refs(
    project_dir: pathlib.Path,
    chunk_id: str,
    chunks: ChunksProtocol | None = None,
) -> list[str]:
    """..."""
    warnings.warn(...)
    from chunks import Chunks
    chunk_mgr = Chunks(project_dir)
    return chunk_mgr.validate_subsystem_refs(chunk_id)
```

This ensures the deprecated functions route through the same code path as the recommended API.

**Location**: `src/integrity.py`, lines 705-913

### Step 6: Update imports in chunks.py

Update `chunks.py` to:
1. Import `IntegrityValidator` and `_errors_to_messages` from `integrity`
2. Remove imports of the four standalone validation functions (they're now deprecated)

The imports currently at lines 65-68:
```python
from integrity import (
    validate_chunk_subsystem_refs,
    validate_chunk_investigation_ref,
    validate_chunk_narrative_ref,
    validate_chunk_friction_entries_ref,
)
```

Should be replaced with:
```python
from integrity import IntegrityValidator, _errors_to_messages
```

**Location**: `src/chunks.py`, lines 65-68

### Step 7: Verify existing tests pass

Run the existing test suites to ensure:
1. `tests/test_chunks.py::TestValidateSubsystemRefs` continues to pass (tests the `Chunks` wrapper methods)
2. `tests/test_integrity.py` continues to pass (tests `IntegrityValidator`)

The wrapper methods should produce identical results to the previous implementation.

**Command**: `uv run pytest tests/test_chunks.py tests/test_integrity.py -v`

### Step 8: Add deprecation warning tests

Add tests to verify that calling the deprecated standalone functions emits `DeprecationWarning`:

```python
def test_validate_chunk_subsystem_refs_emits_deprecation_warning(self, temp_project):
    """Standalone function emits deprecation warning."""
    import warnings
    from integrity import validate_chunk_subsystem_refs

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        validate_chunk_subsystem_refs(temp_project, "nonexistent")

    assert len(w) == 1
    assert issubclass(w[0].category, DeprecationWarning)
    assert "deprecated" in str(w[0].message).lower()
```

**Location**: `tests/test_integrity.py`, new test class `TestDeprecatedStandaloneFunctions`

### Step 9: Update chunk backreferences

Update or remove backreferences in the deprecated functions to point to this chunk, indicating they are deprecated.

The current backreferences like:
```python
# Chunk: docs/chunks/chunks_decompose - Standalone validation functions extracted from Chunks class
# Chunk: docs/chunks/chunks_class_decouple - Accepts ChunksProtocol to break circular import
```

Should be updated to include:
```python
# Chunk: docs/chunks/integrity_deprecate_standalone - Deprecated, use Chunks methods or IntegrityValidator
```

**Location**: `src/integrity.py`, comments above each standalone function

## Dependencies

- **chunks_class_decouple** (ACTIVE): This chunk restructured the `Chunks` class and introduced the `ChunksProtocol` to break circular imports between `chunks.py` and `integrity.py`. With that decoupling in place, there's no longer a reason to maintain the standalone functions as a separate code path.

## Risks and Open Questions

1. **Performance impact of index building**: The new `validate_chunk()` method calls `_build_artifact_index()` and `_build_parent_chunk_index()` which iterate over all artifacts. For single-chunk validation, this is more work than the standalone functions did. However:
   - The `Chunks` wrapper methods are typically called for single-chunk validation during `ve chunk validate` or similar CLI commands
   - The full `IntegrityValidator.validate()` already builds these indexes anyway
   - The index building is O(n) in the number of artifacts, which is typically small (<100)

   **Mitigation**: If profiling shows this is a problem, we can add lazy initialization or caching to the indexes. For now, correctness over optimization.

2. **ChunksProtocol may become unused**: After this change, the `ChunksProtocol` in `integrity.py` may only be used by the deprecated standalone functions. Consider whether to keep it for backward compatibility or remove it entirely in a future cleanup.

3. **Bidirectional warnings**: The standalone functions never returned bidirectional warnings (they only checked existence). The new routing through `IntegrityValidator` does produce warnings, but the `Chunks` wrapper methods only return errors. This is consistent with current behavior but may be surprising to users who expected warnings from `Chunks` methods. The warnings are still available via `IntegrityValidator.validate_chunk()` directly.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->