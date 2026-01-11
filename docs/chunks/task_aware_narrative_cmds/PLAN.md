<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Follow the established pattern from task-aware chunk commands (`create_task_chunk`, `list_task_chunks` in `task_utils.py` and their CLI integration in `ve.py`). The narrative implementation mirrors this structure:

1. **Rename `external_chunk_repo` to `external_artifact_repo`** in `TaskConfig` to reflect that the external repo stores all artifact types (chunks, narratives, investigations, subsystems), not just chunks.

2. **Add task-aware utility functions** to `task_utils.py` following the chunk pattern:
   - `create_task_narrative()` - orchestrate cross-repo narrative creation
   - `list_task_narratives()` - list narratives with dependents from external repo
   - `TaskNarrativeError` - error class for user-friendly messages (or reuse a generic `TaskArtifactError`)

3. **Extend CLI commands** in `ve.py`:
   - Modify `create_narrative` to detect task directory and delegate to `_create_task_narrative()`
   - Modify `list_narratives` to detect task directory and delegate to `_list_task_narratives()`

4. **Add `dependents` field to `NarrativeFrontmatter`** to track cross-repo references (parallel to `ChunkFrontmatter.dependents`).

5. **Test-driven development** per TESTING_PHILOSOPHY.md:
   - Write failing tests first for task-aware narrative create/list
   - Follow the test patterns from `test_task_chunk_create.py` and `test_task_chunk_list.py`

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS task-aware
  narrative commands, extending the external reference pattern from chunks to narratives.
  The subsystem documents the pattern for cross-repository workflow artifacts.

Since the subsystem is in REFACTORING status, any code touched should follow the
established patterns:
- Use `ExternalArtifactRef` (not the legacy `ExternalChunkRef`) for external references
- Use utilities from `external_refs.py` for external artifact operations
- Follow the manager class pattern (`Narratives`) for artifact operations
- Include backreference comments linking to this chunk and the subsystem

## Sequence

### Step 1: Rename TaskConfig.external_chunk_repo to external_artifact_repo

Update `TaskConfig` in `src/models.py`:
- Rename field `external_chunk_repo` to `external_artifact_repo`
- Update the validator method name to `validate_external_artifact_repo`
- Update docstring to reflect that this is for all artifact types

Then update all references in `src/task_utils.py`:
- `create_task_chunk()` - uses `config.external_chunk_repo`
- `list_task_chunks()` - uses `config.external_chunk_repo`
- `get_current_task_chunk()` - uses `config.external_chunk_repo`

Update test files:
- `tests/test_task_chunk_create.py` - uses `external_chunk_repo` in YAML
- `tests/test_task_chunk_list.py` - uses `external_chunk_repo` in YAML
- `tests/test_task_models.py` - tests TaskConfig validation
- Any other test files referencing this field

Location: `src/models.py`, `src/task_utils.py`, `tests/test_task_*.py`

### Step 2: Add dependents field to NarrativeFrontmatter

Update `NarrativeFrontmatter` in `src/models.py`:
- Add `dependents: list[ExternalArtifactRef] = []` field

Update `Narratives._update_overview_frontmatter()` in `src/narratives.py`:
- Ensure it can update the `dependents` field

Location: `src/models.py`, `src/narratives.py`

### Step 3: Write failing tests for task-aware narrative create

Create `tests/test_task_narrative_create.py` with tests mirroring `test_task_chunk_create.py`:

```python
class TestNarrativeCreateInTaskDirectory:
    def test_creates_external_narrative(self, tmp_path):
        """Creates narrative in external repo when in task directory."""

    def test_creates_external_yaml_in_each_project(self, tmp_path):
        """Creates external.yaml in each project's narrative directory."""

    def test_populates_dependents_in_external_narrative(self, tmp_path):
        """Updates external narrative OVERVIEW.md with dependents list."""

    def test_reports_all_created_paths(self, tmp_path):
        """Output includes all created paths."""

class TestNarrativeCreateOutsideTaskDirectory:
    def test_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""

class TestNarrativeCreateErrorHandling:
    def test_error_when_external_repo_inaccessible(self, tmp_path):
        """Reports clear error when external repo directory missing."""

    def test_error_when_project_inaccessible(self, tmp_path):
        """Reports clear error when project directory missing."""
```

Location: `tests/test_task_narrative_create.py`

### Step 4: Implement create_task_narrative in task_utils.py

Add function `create_task_narrative()` following the `create_task_chunk()` pattern:

```python
def create_task_narrative(
    task_dir: Path,
    short_name: str,
) -> dict:
    """Create narrative in task directory context.

    Orchestrates multi-repo narrative creation:
    1. Creates narrative in external repo
    2. Creates external.yaml in each project with causal ordering
    3. Updates external narrative's OVERVIEW.md with dependents

    Returns:
        Dict with keys:
        - external_narrative_path: Path to created narrative in external repo
        - project_refs: Dict mapping project repo ref to created external.yaml path
    """
```

Also add:
- `TaskNarrativeError` exception class (or rename `TaskChunkError` to generic `TaskArtifactError`)
- `add_dependents_to_narrative()` helper function

Location: `src/task_utils.py`

### Step 5: Integrate task-aware narrative create into CLI

Update `create_narrative` command in `ve.py`:

```python
@narrative.command("create")
@click.argument("short_name")
@click.option("--project-dir", ...)
def create_narrative(short_name, project_dir):
    """Create a new narrative."""
    # Existing validation...

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _create_task_narrative(project_dir, short_name)
        return

    # Existing single-repo logic...
```

Add helper function `_create_task_narrative()` following `_start_task_chunk()` pattern.

Location: `src/ve.py`

### Step 6: Run tests and verify narrative create works

Run the test suite to verify:
- All new tests in `test_task_narrative_create.py` pass
- All existing tests still pass

```bash
uv run pytest tests/test_task_narrative_create.py -v
uv run pytest tests/ -v
```

### Step 7: Write failing tests for task-aware narrative list

Create `tests/test_task_narrative_list.py` with tests mirroring `test_task_chunk_list.py`:

```python
class TestNarrativeListInTaskDirectory:
    def test_lists_narratives_from_external_repo(self, tmp_path):
        """Lists narratives from external repo, not local project."""

    def test_shows_dependents_for_each_narrative(self, tmp_path):
        """Displays dependents info for narratives with cross-repo refs."""

    def test_shows_status(self, tmp_path):
        """Displays narrative status."""

class TestNarrativeListOutsideTaskDirectory:
    def test_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
```

Location: `tests/test_task_narrative_list.py`

### Step 8: Implement list_task_narratives in task_utils.py

Add function `list_task_narratives()` following the `list_task_chunks()` pattern:

```python
def list_task_narratives(task_dir: Path) -> list[dict]:
    """List narratives from external repo with their dependents.

    Returns:
        List of dicts with keys: name, status, dependents
    """
```

Location: `src/task_utils.py`

### Step 9: Integrate task-aware narrative list into CLI

Update `list_narratives` command in `ve.py`:

```python
@narrative.command("list")
@click.option("--project-dir", ...)
def list_narratives(project_dir):
    """List all narratives."""
    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_narratives(project_dir)
        return

    # Existing single-repo logic...
```

Add helper function `_list_task_narratives()` following `_list_task_chunks()` pattern.

Location: `src/ve.py`

### Step 10: Run full test suite and verify

Run the complete test suite:

```bash
uv run pytest tests/ -v
```

Verify:
- All task-aware narrative tests pass
- All existing tests still pass
- No regressions in chunk functionality

## Dependencies

- **consolidate_ext_ref_utils chunk** (completed): Provides the `external_refs.py` module
  with `is_external_artifact()`, `create_external_yaml()`, `load_external_ref()` that we'll
  use for narrative external references.

- **consolidate_ext_refs chunk** (completed): Provides `ExternalArtifactRef` model that
  supports all artifact types via `artifact_type` field.

## Risks and Open Questions

1. **Error class naming**: Should we create `TaskNarrativeError` or refactor to a generic
   `TaskArtifactError`? The chunk pattern uses `TaskChunkError`, suggesting per-type
   error classes. For consistency, use `TaskNarrativeError` now; generalization can be
   a future consolidation task.

2. **Template for narrative OVERVIEW.md dependents**: The narrative template may not
   include a `dependents` field. Need to verify if the template needs updating or if
   we add it only when needed (like chunks do via `add_dependents_to_chunk`).

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