<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The implementation follows the existing pattern for directory creation in `project.py`. The `_init_narratives()` method provides a direct template: check if directory exists, create if not, report to InitResult.

We will add a new `_init_chunks()` method that mirrors `_init_narratives()` and integrate it into the `init()` method's list of sub-results.

Tests follow TDD and the patterns established in `test_project.py` and `test_init.py`.

## Subsystem Considerations

No subsystems are relevant to this change.

## Sequence

### Step 1: Write failing tests for `_init_chunks()` and Project.init()

Add tests to `tests/test_project.py` that verify:
1. `init()` creates `docs/chunks/` directory
2. `init()` reports `docs/chunks/` in the created list
3. `init()` skips `docs/chunks/` if it already exists (idempotent)

Location: `tests/test_project.py`

### Step 2: Write failing CLI test for output

Add test to `tests/test_init.py` that verifies:
1. `ve init` includes `docs/chunks/` in its "Created" output

Location: `tests/test_init.py`

### Step 3: Implement `_init_chunks()` method

Add a new method to the `Project` class in `src/project.py` that creates the `docs/chunks/` directory following the same pattern as `_init_narratives()`:

```python
def _init_chunks(self) -> InitResult:
    """Create docs/chunks/ directory for chunk documents."""
    result = InitResult()
    chunks_dir = self.project_dir / "docs" / "chunks"

    if chunks_dir.exists():
        result.skipped.append("docs/chunks/")
    else:
        chunks_dir.mkdir(parents=True, exist_ok=True)
        result.created.append("docs/chunks/")

    return result
```

Add backreference comment linking to this chunk.

Location: `src/project.py`

### Step 4: Integrate into `init()` method

Update the `init()` method in `src/project.py` to call `_init_chunks()` in its list of sub-results.

Location: `src/project.py`

### Step 5: Run tests and verify all pass

Run the full test suite to ensure:
1. New tests pass
2. Existing tests continue to pass
3. A freshly initialized project passes `ve task init` validation

```bash
uv run pytest tests/
```

## Dependencies

None. This chunk builds on existing infrastructure in `project.py`.

## Risks and Open Questions

None identified. The implementation mirrors existing patterns with no novel complexity.

## Deviations

<!-- Populate during implementation if the plan changes. -->