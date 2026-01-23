<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Follow the established pattern from task-aware narrative commands (`create_task_narrative`, `list_task_narratives` in `task_utils.py` and their CLI integration in `ve.py`). The subsystem implementation mirrors this structure:

1. **Add `dependents` field to `SubsystemFrontmatter`** in `models.py` to track cross-repo references (parallel to `NarrativeFrontmatter.dependents`).

2. **Add task-aware utility functions** to `task_utils.py` following the narrative pattern:
   - `create_task_subsystem()` - orchestrate cross-repo subsystem creation
   - `list_task_subsystems()` - list subsystems with dependents from external repo
   - `add_dependents_to_subsystem()` - update subsystem OVERVIEW.md frontmatter with dependents
   - `TaskSubsystemError` - error class for user-friendly messages

3. **Extend CLI commands** in `ve.py`:
   - Modify `discover` to detect task directory and delegate to `_create_task_subsystem()`
   - Modify `list_subsystems` to detect task directory and delegate to `_list_task_subsystems()`

4. **Test-driven development** per TESTING_PHILOSOPHY.md:
   - Write failing tests first for task-aware subsystem discover/list
   - Follow the test patterns from `test_task_narrative_create.py` and `test_task_narrative_list.py`

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS task-aware
  subsystem commands, extending the external reference pattern to subsystems.
  The subsystem documents the pattern for cross-repository workflow artifacts.

Since the subsystem is in REFACTORING status, any code touched should follow the
established patterns:
- Use `ExternalArtifactRef` for external references
- Use utilities from `external_refs.py` for external artifact operations
- Follow the manager class pattern (`Subsystems`) for artifact operations
- Include backreference comments linking to this chunk and the subsystem

## Sequence

### Step 1: Add dependents field to SubsystemFrontmatter

Update `SubsystemFrontmatter` in `src/models.py`:
- Add `dependents: list[ExternalArtifactRef] = []` field

Location: `src/models.py`

### Step 2: Write failing tests for task-aware subsystem discover

Create `tests/test_task_subsystem_discover.py` with tests mirroring `test_task_narrative_create.py`:

```python
class TestSubsystemDiscoverInTaskDirectory:
    def test_creates_external_subsystem(self, tmp_path):
        """Creates subsystem in external repo when in task directory."""

    def test_creates_external_yaml_in_each_project(self, tmp_path):
        """Creates external.yaml in each project's subsystem directory."""

    def test_populates_dependents_in_external_subsystem(self, tmp_path):
        """Updates external subsystem OVERVIEW.md with dependents list."""

    def test_reports_all_created_paths(self, tmp_path):
        """Output includes all created paths."""

class TestSubsystemDiscoverOutsideTaskDirectory:
    def test_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""

class TestSubsystemDiscoverErrorHandling:
    def test_error_when_external_repo_inaccessible(self, tmp_path):
        """Reports clear error when external repo directory missing."""

    def test_error_when_project_inaccessible(self, tmp_path):
        """Reports clear error when project directory missing."""
```

Location: `tests/test_task_subsystem_discover.py`

### Step 3: Implement TaskSubsystemError and add_dependents_to_subsystem in task_utils.py

Add to `task_utils.py`:

```python
# Chunk: docs/chunks/task_aware_subsystem_cmds - Task subsystem error class
class TaskSubsystemError(Exception):
    """Error during task subsystem creation with user-friendly message."""
    pass


# Chunk: docs/chunks/task_aware_subsystem_cmds - Add dependents to subsystem
def add_dependents_to_subsystem(
    subsystem_path: Path,
    dependents: list[dict],
) -> None:
    """Update subsystem OVERVIEW.md frontmatter to include dependents list.

    Args:
        subsystem_path: Path to the subsystem directory containing OVERVIEW.md
        dependents: List of {artifact_type, artifact_id, repo} dicts to add as dependents

    Raises:
        FileNotFoundError: If OVERVIEW.md doesn't exist in subsystem_path
    """
```

Location: `src/task_utils.py`

### Step 4: Implement create_task_subsystem in task_utils.py

Add function `create_task_subsystem()` following the `create_task_narrative()` pattern:

```python
# Chunk: docs/chunks/task_aware_subsystem_cmds - Orchestrate multi-repo subsystem
def create_task_subsystem(
    task_dir: Path,
    short_name: str,
) -> dict:
    """Create subsystem in task directory context.

    Orchestrates multi-repo subsystem creation:
    1. Creates subsystem in external repo
    2. Creates external.yaml in each project with causal ordering
    3. Updates external subsystem's OVERVIEW.md with dependents

    Returns:
        Dict with keys:
        - external_subsystem_path: Path to created subsystem in external repo
        - project_refs: Dict mapping project repo ref to created external.yaml path

    Raises:
        TaskSubsystemError: If any step fails, with user-friendly message
    """
```

Location: `src/task_utils.py`

### Step 5: Integrate task-aware subsystem discover into CLI

Update `discover` command in `ve.py`:

```python
@subsystem.command()
@click.argument("shortname")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def discover(shortname, project_dir):
    """Create a new subsystem."""
    errors = validate_short_name(shortname)
    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Normalize to lowercase
    shortname = shortname.lower()

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _create_task_subsystem(project_dir, shortname)
        return

    # Existing single-repo logic...
```

Add helper function `_create_task_subsystem()` following `_create_task_narrative()` pattern.

Location: `src/ve.py`

### Step 6: Run tests and verify subsystem discover works

Run the test suite to verify:
- All new tests in `test_task_subsystem_discover.py` pass
- All existing tests still pass

```bash
uv run pytest tests/test_task_subsystem_discover.py -v
uv run pytest tests/ -v
```

### Step 7: Write failing tests for task-aware subsystem list

Create `tests/test_task_subsystem_list.py` with tests mirroring `test_task_narrative_list.py`:

```python
class TestSubsystemListInTaskDirectory:
    def test_lists_subsystems_from_external_repo(self, tmp_path):
        """Lists subsystems from external repo, not local project."""

    def test_shows_dependents_for_each_subsystem(self, tmp_path):
        """Displays dependents info for subsystems with cross-repo refs."""

    def test_shows_status(self, tmp_path):
        """Displays subsystem status."""

class TestSubsystemListOutsideTaskDirectory:
    def test_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
```

Location: `tests/test_task_subsystem_list.py`

### Step 8: Implement list_task_subsystems in task_utils.py

Add function `list_task_subsystems()` following the `list_task_narratives()` pattern:

```python
# Chunk: docs/chunks/task_aware_subsystem_cmds - Task-aware subsystem listing
def list_task_subsystems(task_dir: Path) -> list[dict]:
    """List subsystems from external repo with their dependents.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        List of dicts with keys: name, status, dependents
        Sorted by causal ordering (newest first).

    Raises:
        TaskSubsystemError: If external repo not accessible
    """
```

Location: `src/task_utils.py`

### Step 9: Integrate task-aware subsystem list into CLI

Update `list_subsystems` command in `ve.py`:

```python
@subsystem.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_subsystems(project_dir):
    """List all subsystems."""
    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_subsystems(project_dir)
        return

    # Existing single-repo logic...
```

Add helper function `_list_task_subsystems()` following `_list_task_narratives()` pattern.

Location: `src/ve.py`

### Step 10: Run full test suite and verify

Run the complete test suite:

```bash
uv run pytest tests/ -v
```

Verify:
- All task-aware subsystem tests pass
- All existing tests still pass
- No regressions in narrative or chunk functionality

## Dependencies

- **consolidate_ext_ref_utils chunk** (completed): Provides the `external_refs.py` module
  with `is_external_artifact()`, `create_external_yaml()`, `load_external_ref()` that we'll
  use for subsystem external references.

- **consolidate_ext_refs chunk** (completed): Provides `ExternalArtifactRef` model that
  supports all artifact types via `artifact_type` field.

- **task_aware_narrative_cmds chunk** (completed): Provides the pattern to follow for
  task-aware subsystem commands, including `TaskNarrativeError`, `create_task_narrative()`,
  `list_task_narratives()`, and CLI integration.

## Risks and Open Questions

1. **Subsystem template for dependents**: The subsystem template may not include a `dependents`
   field. We'll add it only when needed via `add_dependents_to_subsystem()`, similar to
   how chunks and narratives do it via `add_dependents_to_chunk()` and `add_dependents_to_narrative()`.

2. **Validation during discover**: The current `discover` command validates the shortname
   and checks for duplicates before creation. When in task directory mode, we need to ensure
   these validations happen against the external repo, not the task directory itself.

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
-->