<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extracts duplicated YAML frontmatter parsing and updating logic from ~10
implementations across the codebase into a single shared utility module (`src/frontmatter.py`).

The implementation follows a "build then migrate" strategy:
1. Create the new `src/frontmatter.py` module with a generic interface
2. Write comprehensive tests for the new module
3. Migrate each call site one at a time, running tests after each migration
4. Verify no functional changes occurred (pure refactor)

The new module provides two main entry points:
- `parse_frontmatter(file_path, model_class)` - Read, extract, parse, validate
- `update_frontmatter_field(file_path, field, value)` - Read, update, write

These encapsulate the common pattern currently duplicated across:
- `chunks.py`: `parse_chunk_frontmatter()`, `parse_chunk_frontmatter_with_errors()`, `_parse_frontmatter_from_content()`
- `narratives.py`: `parse_narrative_frontmatter()`, `_update_overview_frontmatter()`
- `investigations.py`: `parse_investigation_frontmatter()`, `_update_overview_frontmatter()`
- `subsystems.py`: `parse_subsystem_frontmatter()`, `_update_overview_frontmatter()`
- `friction.py`: `parse_frontmatter()`
- `artifact_ordering.py`: `_parse_frontmatter()`
- `task_utils.py`: `update_frontmatter_field()`

**Testing approach** (per TESTING_PHILOSOPHY.md):
- Write tests for the new module first (behavior-driven tests)
- Verify migrations don't break existing behavior by running full test suite after each change
- Focus on boundary conditions: missing files, malformed YAML, validation failures

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS a shared
  utility that the workflow artifact managers (Chunks, Narratives, Investigations,
  Subsystems) will use. The new `src/frontmatter.py` module becomes a foundational
  utility for the workflow artifact subsystem.

The workflow_artifacts subsystem documents the manager class pattern:
> **Manager class must implement the core interface** - Every workflow type needs:
> - `enumerate_{types}()` - list artifact directories
> - `create_{type}(short_name)` - instantiate new artifact
> - `parse_{type}_frontmatter()` - parse and validate frontmatter

This chunk extracts the common implementation of `parse_*_frontmatter()` and
`_update_overview_frontmatter()` into shared utilities. The manager classes will
continue to provide their type-specific interfaces but delegate to `src/frontmatter.py`
for the I/O operations.

After this chunk completes, a code_reference should be added to the workflow_artifacts
subsystem OVERVIEW.md for `src/frontmatter.py#parse_frontmatter` and
`src/frontmatter.py#update_frontmatter_field`.

## Sequence

### Step 1: Create `src/frontmatter.py` with core parsing logic

Create the new module with:

```python
# Chunk: docs/chunks/frontmatter_io - Shared frontmatter I/O utilities
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

def parse_frontmatter(
    file_path: Path,
    model_class: type[T],
) -> T | None:
    """Parse YAML frontmatter from a markdown file and validate with Pydantic model."""

def parse_frontmatter_with_errors(
    file_path: Path,
    model_class: type[T],
) -> tuple[T | None, list[str]]:
    """Parse frontmatter returning both result and detailed validation errors."""

def parse_frontmatter_from_content(
    content: str,
    model_class: type[T],
) -> T | None:
    """Parse frontmatter from content string (for cache-based resolution)."""

def update_frontmatter_field(
    file_path: Path,
    field: str,
    value: Any,
) -> None:
    """Update a single field in a file's YAML frontmatter."""
```

The implementation extracts the common pattern:
1. Read file content (or use provided content string)
2. Regex match `^---\s*\n(.*?)\n---` to extract frontmatter YAML
3. Parse with `yaml.safe_load()`
4. Validate with provided Pydantic model's `model_validate()`
5. Return validated model or None (with optional error details)

For updates:
1. Read file content
2. Regex match to separate frontmatter from body
3. Parse frontmatter YAML to dict
4. Update the field
5. Dump back to YAML and write file

Location: `src/frontmatter.py`

### Step 2: Write tests for `src/frontmatter.py`

Create `tests/test_frontmatter.py` with tests for:

**parse_frontmatter tests:**
- Valid frontmatter parses and validates correctly
- Missing file returns None
- File without frontmatter markers returns None
- Invalid YAML returns None
- YAML that fails Pydantic validation returns None

**parse_frontmatter_with_errors tests:**
- Valid frontmatter returns (model, [])
- Invalid file returns (None, [error_msg])
- YAML parse error returns appropriate error message
- Pydantic validation errors are formatted as field-specific messages

**parse_frontmatter_from_content tests:**
- Valid content string parses correctly
- Invalid content returns None

**update_frontmatter_field tests:**
- Existing field is updated correctly
- New field is added correctly
- Body content is preserved unchanged
- Missing file raises FileNotFoundError
- File without frontmatter raises ValueError

Use a simple test model (e.g., `TestFrontmatter`) for isolation from real artifact models.

Location: `tests/test_frontmatter.py`

### Step 3: Migrate `chunks.py` parsing functions

Update `chunks.py` to use the new shared utilities:

**parse_chunk_frontmatter():**
```python
def parse_chunk_frontmatter(self, chunk_id: str) -> ChunkFrontmatter | None:
    frontmatter, _ = self.parse_chunk_frontmatter_with_errors(chunk_id)
    return frontmatter
```

**parse_chunk_frontmatter_with_errors():**
```python
def parse_chunk_frontmatter_with_errors(
    self, chunk_id: str
) -> tuple[ChunkFrontmatter | None, list[str]]:
    goal_path = self.get_chunk_goal_path(chunk_id)
    if goal_path is None or not goal_path.exists():
        return None, [f"Chunk '{chunk_id}' not found"]

    from frontmatter import parse_frontmatter_with_errors
    return parse_frontmatter_with_errors(goal_path, ChunkFrontmatter)
```

**_parse_frontmatter_from_content():**
```python
def _parse_frontmatter_from_content(self, content: str) -> ChunkFrontmatter | None:
    from frontmatter import parse_frontmatter_from_content
    return parse_frontmatter_from_content(content, ChunkFrontmatter)
```

Remove the duplicated regex/yaml/pydantic code.

Run tests: `uv run pytest tests/test_chunks.py tests/test_chunk_*.py`

### Step 4: Migrate `narratives.py`

Update `narratives.py` to use the shared utilities:

**parse_narrative_frontmatter():**
```python
def parse_narrative_frontmatter(self, narrative_id: str) -> NarrativeFrontmatter | None:
    overview_path = self.narratives_dir / narrative_id / "OVERVIEW.md"
    if not overview_path.exists():
        return None

    from frontmatter import parse_frontmatter

    # Handle legacy 'chunks' field by mapping to 'proposed_chunks'
    # Need to parse raw YAML first, then remap
    ...
```

**Note:** The narrative frontmatter has a legacy field mapping (`chunks` → `proposed_chunks`).
This can be handled via a pre-parse hook or by keeping a thin wrapper that does the remapping
before calling the shared parser.

**_update_overview_frontmatter():**
```python
def _update_overview_frontmatter(self, narrative_id: str, field: str, value) -> None:
    overview_path = self.narratives_dir / narrative_id / "OVERVIEW.md"
    from frontmatter import update_frontmatter_field
    update_frontmatter_field(overview_path, field, value)
```

Run tests: `uv run pytest tests/test_narratives.py tests/test_narrative_*.py`

### Step 5: Migrate `investigations.py`

Update `investigations.py` to use the shared utilities:

**parse_investigation_frontmatter():**
```python
def parse_investigation_frontmatter(self, investigation_id: str) -> InvestigationFrontmatter | None:
    overview_path = self.investigations_dir / investigation_id / "OVERVIEW.md"
    if not overview_path.exists():
        return None

    from frontmatter import parse_frontmatter
    return parse_frontmatter(overview_path, InvestigationFrontmatter)
```

**_update_overview_frontmatter():**
```python
def _update_overview_frontmatter(self, investigation_id: str, field: str, value) -> None:
    overview_path = self.investigations_dir / investigation_id / "OVERVIEW.md"
    from frontmatter import update_frontmatter_field
    update_frontmatter_field(overview_path, field, value)
```

Run tests: `uv run pytest tests/test_investigations.py tests/test_investigation_*.py`

### Step 6: Migrate `subsystems.py`

Update `subsystems.py` to use the shared utilities:

**parse_subsystem_frontmatter():**
```python
def parse_subsystem_frontmatter(self, subsystem_id: str) -> SubsystemFrontmatter | None:
    overview_path = self.subsystems_dir / subsystem_id / "OVERVIEW.md"
    if not overview_path.exists():
        return None

    from frontmatter import parse_frontmatter
    return parse_frontmatter(overview_path, SubsystemFrontmatter)
```

**_update_overview_frontmatter():**
```python
def _update_overview_frontmatter(self, subsystem_id: str, field: str, value) -> None:
    overview_path = self.subsystems_dir / subsystem_id / "OVERVIEW.md"
    from frontmatter import update_frontmatter_field
    update_frontmatter_field(overview_path, field, value)
```

Run tests: `uv run pytest tests/test_subsystems.py tests/test_subsystem_*.py`

### Step 7: Migrate `friction.py`

Update `friction.py` to use the shared utilities:

**parse_frontmatter():**
```python
def parse_frontmatter(self) -> FrictionFrontmatter | None:
    if not self.exists():
        return None

    from frontmatter import parse_frontmatter as parse_fm
    return parse_fm(self.friction_path, FrictionFrontmatter)
```

Run tests: `uv run pytest tests/test_friction.py tests/test_friction_*.py`

### Step 8: Migrate `artifact_ordering.py`

Update `artifact_ordering.py` to use the shared utilities:

**_parse_frontmatter():**
The existing `_parse_frontmatter()` in artifact_ordering.py returns a raw dict,
not a Pydantic model. This is used to extract `created_after` and `status` fields
generically across artifact types.

Create a new helper in `src/frontmatter.py`:
```python
def extract_frontmatter_dict(file_path: Path) -> dict[str, Any] | None:
    """Extract raw frontmatter dict without Pydantic validation."""
```

Then migrate `_parse_frontmatter()` to use it.

Run tests: `uv run pytest tests/test_artifact_ordering.py`

### Step 9: Migrate `task_utils.py`

The `update_frontmatter_field()` in task_utils.py is identical to the pattern we're
consolidating. After Step 1, update imports to use the shared version:

```python
# At module level or in functions that need it:
from frontmatter import update_frontmatter_field
```

Remove the local `update_frontmatter_field()` definition and update all call sites
within task_utils.py to use the imported version.

Run tests: `uv run pytest tests/test_task_*.py`

### Step 10: Run full test suite and verify no regressions

```bash
uv run pytest tests/
```

All existing tests must pass. This validates that the refactoring hasn't changed
any observable behavior.

### Step 11: Update GOAL.md code_paths with files touched

Update the chunk's GOAL.md frontmatter `code_paths` field to reflect the files
created and modified:

```yaml
code_paths:
  - src/frontmatter.py
  - tests/test_frontmatter.py
  - src/chunks.py
  - src/narratives.py
  - src/investigations.py
  - src/subsystems.py
  - src/friction.py
  - src/artifact_ordering.py
  - src/task_utils.py
```

## Dependencies

No external dependencies. Uses existing libraries already in pyproject.toml:
- `pyyaml` for YAML parsing
- `pydantic` for model validation

No chunk dependencies - this is a foundational refactoring.

## Risks and Open Questions

1. **Narrative legacy field mapping** - `narratives.py` remaps `chunks` to `proposed_chunks`
   before Pydantic validation. Options:
   - Keep thin wrapper in Narratives that does remapping before calling shared parser
   - Add optional `pre_transform` callback to shared parser
   - Handle in Pydantic model with field aliases

   **Recommendation:** Keep thin wrapper for clarity; the legacy handling is narrative-specific.

2. **artifact_ordering.py needs raw dict** - The `_parse_frontmatter()` in artifact_ordering.py
   returns a raw dict, not a Pydantic model. It's used for generic field extraction across
   artifact types.

   **Solution:** Add `extract_frontmatter_dict()` to the shared module for this use case.

3. **Import cycles** - `frontmatter.py` must not import artifact modules (chunks, narratives, etc.)
   to avoid circular imports. The module should be generic, taking the model class as a parameter.

   **Mitigation:** Design the API to receive model classes as parameters, not import them.

4. **Error message format changes** - Some callers may depend on specific error message formats.

   **Mitigation:** Run full test suite after each migration to catch any format dependencies.

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