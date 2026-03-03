<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extract the file manipulation logic from `src/cli/narrative.py:compact()` (lines 233-304) into a new `Narratives.compact()` domain method in `src/narratives.py`. This follows the existing layering pattern where CLI commands delegate file I/O to domain classes.

The approach:
1. Create `Narratives.compact()` method that accepts validated chunk IDs and description
2. The method reuses `create_narrative()` to create the directory, then uses `frontmatter.py` utilities (`extract_frontmatter_dict`, `update_frontmatter_field` pattern) to update the OVERVIEW.md frontmatter
3. Refactor the CLI `compact` command to delegate to the domain method, keeping only input validation (chunk existence via `Chunks`) and output formatting

This aligns with:
- **DEC-009 (ArtifactManager Template Method Pattern)**: The `Narratives` class already follows the manager pattern; adding `compact()` extends it consistently
- **workflow_artifacts subsystem (Hard Invariant #6)**: Manager classes implement the core interface; adding domain methods follows this pattern

The existing `frontmatter.py` module provides `extract_frontmatter_dict()` and `update_frontmatter_field()`. However, `update_frontmatter_field()` updates a single field at a time. For `compact()` we need to update two fields (`proposed_chunks` and `advances_trunk_goal`). We can either:
1. Call `update_frontmatter_field()` twice (simple but reads/writes file twice)
2. Add a new `update_frontmatter_fields()` helper for batch updates

Option 1 is simpler and the file is small; the double read/write is negligible. We'll use that.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS the extraction of domain logic from CLI to the `Narratives` manager class, following the subsystem's manager class pattern (Hard Invariant #6: "Manager class must implement the core interface"). The `compact()` method being added follows the pattern established by other manager methods like `create_narrative()`.

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system indirectly via `create_narrative()` which already delegates to `render_to_directory()`.

The existing `compact` CLI command is a deviation from the workflow_artifacts subsystem pattern -- it directly manipulates files rather than delegating to the domain layer. This chunk resolves that deviation.

## Sequence

### Step 1: Write failing tests for `Narratives.compact()`

Create a new test class `TestNarrativeCompact` in `tests/test_narratives.py` that verifies:
1. `compact()` creates a narrative directory with OVERVIEW.md
2. `compact()` populates `proposed_chunks` in frontmatter with entries for each chunk ID
3. `compact()` populates `advances_trunk_goal` with the provided description
4. `compact()` returns the created narrative path
5. `compact()` raises `ValueError` if the narrative name already exists (collision detection)

These tests should fail initially because `Narratives.compact()` doesn't exist yet.

Location: `tests/test_narratives.py`

### Step 2: Implement `Narratives.compact()` domain method

Add the `compact()` method to the `Narratives` class in `src/narratives.py`:

```python
def compact(self, chunk_ids: list[str], name: str, description: str) -> pathlib.Path:
    """Consolidate chunks into a narrative.

    Creates a new narrative and populates its frontmatter with references to
    the consolidated chunks.

    Args:
        chunk_ids: List of chunk directory names to consolidate
        name: Short name for the narrative (already validated)
        description: Description to set in advances_trunk_goal

    Returns:
        Path to the created narrative directory

    Raises:
        ValueError: If narrative with same name already exists
    """
```

Implementation:
1. Call `self.create_narrative(name)` to create the directory (reuses collision detection)
2. Build the `proposed_chunks` list: `[{"prompt": f"Consolidated from {chunk_id}", "chunk_directory": chunk_id} for chunk_id in chunk_ids]`
3. Call `update_frontmatter_field()` for `proposed_chunks`
4. Call `update_frontmatter_field()` for `advances_trunk_goal` with the description
5. Return the narrative path

Import `update_frontmatter_field` from `frontmatter` module.

Location: `src/narratives.py`

Backreference to add:
```python
# Chunk: docs/chunks/narrative_compact_extract - Domain method for compact command
```

### Step 3: Verify Step 1 tests now pass

Run the tests from Step 1. They should now pass since `Narratives.compact()` is implemented.

Command: `uv run pytest tests/test_narratives.py::TestNarrativeCompact -v`

### Step 4: Refactor CLI `compact` command to delegate to domain method

Modify `src/cli/narrative.py:compact()` to:
1. Keep the input validation (chunk existence via `Chunks.enumerate_chunks()`)
2. Remove the inline file manipulation code (regex, yaml imports, direct file read/write)
3. Call `narratives.compact(normalized_ids, name, description)` instead
4. Keep the CLI output formatting

Remove these imports from the function body:
- `import re`
- `import yaml`

The refactored function should be approximately 20 lines shorter.

Location: `src/cli/narrative.py`

### Step 5: Verify CLI integration tests still pass

Run the existing CLI tests for `narrative compact` to verify behavior is unchanged.

Command: `uv run pytest tests/test_narrative_consolidation.py -v -k "compact or consolidate"`

Also run the full test suite to verify no regressions:

Command: `uv run pytest tests/ -v`

### Step 6: Verify success criteria

Confirm all success criteria are met:
- [ ] `Narratives.compact()` exists and returns the created narrative path
- [ ] It uses `create_narrative()` internally
- [ ] It uses `update_frontmatter_field()` from `frontmatter.py`
- [ ] CLI `compact` command no longer imports `re` or `yaml` directly
- [ ] CLI `compact` command no longer contains regex patterns or `yaml.safe_load`/`yaml.dump` calls
- [ ] All existing tests pass

## Dependencies

No external dependencies. This chunk relies on:
- `src/frontmatter.py` - Already exists with `update_frontmatter_field()`
- `src/narratives.py` - Already exists with `Narratives` class and `create_narrative()`
- `src/cli/narrative.py` - Already exists with the `compact` command to refactor

## Risks and Open Questions

1. **YAML formatting consistency**: The existing CLI code uses `yaml.dump()` with `default_flow_style=False, sort_keys=False`. The `update_frontmatter_field()` utility also uses `yaml.dump()` with the same options, so formatting should be consistent. However, calling it twice means two read/write cycles. If this becomes a concern, we could add a `update_frontmatter_fields()` batch helper -- but for this small file, it's likely fine.

2. **Error handling for create_narrative failures**: If `create_narrative()` raises a `ValueError` (e.g., duplicate name), the `compact()` method will propagate it. The CLI already handles this case, so no additional error handling is needed in the domain method.

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