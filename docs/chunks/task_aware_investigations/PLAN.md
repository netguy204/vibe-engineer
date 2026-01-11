<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extends the investigation commands (`ve investigation create` and `ve investigation list`) to support task directory context, following the exact pattern established by the task-aware narrative commands implemented in chunk `task_aware_narrative_cmds`.

The implementation will:
1. Add `InvestigationDependent` model and `dependents` field to `InvestigationFrontmatter` (following `NarrativeFrontmatter` pattern)
2. Add task-aware utility functions to `task_utils.py` (`TaskInvestigationError`, `create_task_investigation()`, `list_task_investigations()`, `add_dependents_to_investigation()`)
3. Modify CLI commands in `ve.py` to detect task directory context and delegate to task-aware handlers
4. Create integration tests following the patterns in `test_task_narrative_create.py` and `test_task_narrative_list.py`

The approach maintains DEC-002 compliance (git not assumed for basic operations) and follows the established `external.yaml` pattern for cross-repo references.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS the task-aware investigation commands as documented in the subsystem's proposed chunks. The implementation follows the established patterns for external references (`ExternalArtifactRef`), causal ordering (`created_after`), and task directory detection (`is_task_directory()`).

## Sequence

### Step 1: Add InvestigationDependent model and dependents field to InvestigationFrontmatter

Update `src/models.py` to add the `dependents` field to `InvestigationFrontmatter`, following the pattern from `NarrativeFrontmatter`:

```python
class InvestigationFrontmatter(BaseModel):
    """Frontmatter schema for investigation OVERVIEW.md files."""

    status: InvestigationStatus
    trigger: str | None = None
    proposed_chunks: list[ProposedChunk] = []
    created_after: list[str] = []
    dependents: list[ExternalArtifactRef] = []  # For cross-repo investigations
```

Location: `src/models.py`

### Step 2: Add TaskInvestigationError class to task_utils.py

Add a new error class for task investigation operations, following the pattern from `TaskNarrativeError`:

```python
class TaskInvestigationError(Exception):
    """Error during task investigation creation with user-friendly message."""
    pass
```

Location: `src/task_utils.py`

### Step 3: Add add_dependents_to_investigation() function

Add a helper function to update investigation OVERVIEW.md frontmatter with dependents, following the pattern from `add_dependents_to_narrative()`:

```python
def add_dependents_to_investigation(
    investigation_path: Path,
    dependents: list[dict],
) -> None:
    """Update investigation OVERVIEW.md frontmatter to include dependents list."""
```

Location: `src/task_utils.py`

### Step 4: Write failing tests for create_task_investigation()

Create `tests/test_task_investigation_create.py` with tests that verify:
- Creates investigation in external repo when in task directory
- Creates `external.yaml` in each project's `docs/investigations/` directory
- Populates dependents in external investigation's OVERVIEW.md
- Resolves pinned SHA from external repo
- Reports all created paths
- Handles error when external repo inaccessible
- Handles error when project inaccessible
- Single-repo behavior unchanged when not in task directory

Follow the test patterns from `tests/test_task_narrative_create.py`.

Location: `tests/test_task_investigation_create.py`

### Step 5: Implement create_task_investigation() function

Implement the orchestration function for multi-repo investigation creation, following the pattern from `create_task_narrative()`:

```python
def create_task_investigation(
    task_dir: Path,
    short_name: str,
) -> dict:
    """Create investigation in task directory context.

    Orchestrates multi-repo investigation creation:
    1. Creates investigation in external repo
    2. Creates external.yaml in each project with causal ordering
    3. Updates external investigation's OVERVIEW.md with dependents

    Returns:
        Dict with keys:
        - external_investigation_path: Path to created investigation in external repo
        - project_refs: Dict mapping project repo ref to created external.yaml path
    """
```

Location: `src/task_utils.py`

### Step 6: Modify create_investigation CLI command for task directory detection

Update the `create_investigation` command in `ve.py` to detect task directory context and delegate to a task-aware handler:

```python
@investigation.command("create")
@click.argument("short_name")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def create_investigation(short_name, project_dir):
    """Create a new investigation."""
    # ... validation ...

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _create_task_investigation(project_dir, short_name)
        return

    # Single-repo mode (existing behavior)
    # ...
```

Add the helper function `_create_task_investigation()` following the pattern from `_create_task_narrative()`.

Location: `src/ve.py`

### Step 7: Run tests for create functionality

Run `pytest tests/test_task_investigation_create.py` to verify the create functionality works correctly.

### Step 8: Write failing tests for list_task_investigations()

Create `tests/test_task_investigation_list.py` with tests that verify:
- Lists investigations from external repo when in task directory
- Shows dependents for each investigation
- Shows status
- Handles error when external repo inaccessible
- Handles "No investigations found" case
- Single-repo behavior unchanged when not in task directory

Follow the test patterns from `tests/test_task_narrative_list.py`.

Location: `tests/test_task_investigation_list.py`

### Step 9: Implement list_task_investigations() function

Implement the function to list investigations from external repo with their dependents, following the pattern from `list_task_narratives()`:

```python
def list_task_investigations(task_dir: Path) -> list[dict]:
    """List investigations from external repo with their dependents.

    Returns:
        List of dicts with keys: name, status, dependents
        Sorted by investigation name descending.
    """
```

Location: `src/task_utils.py`

### Step 10: Modify list_investigations CLI command for task directory detection

Update the `list_investigations` command in `ve.py` to detect task directory context and delegate to a task-aware handler:

```python
@investigation.command("list")
@click.option("--state", type=str, default=None, help="Filter by investigation state")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_investigations(state, project_dir):
    """List all investigations."""
    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_investigations(project_dir)
        return

    # Single-repo mode (existing behavior)
    # ...
```

Add the helper function `_list_task_investigations()` following the pattern from `_list_task_narratives()`.

Location: `src/ve.py`

### Step 11: Run all tests

Run `pytest tests/` to verify all tests pass, including the new investigation tests and existing tests.

### Step 12: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the files touched during implementation:
- `src/models.py`
- `src/task_utils.py`
- `src/ve.py`
- `tests/test_task_investigation_create.py`
- `tests/test_task_investigation_list.py`

Location: `docs/chunks/task_aware_investigations/GOAL.md`

## Dependencies

- **chunk consolidate_ext_ref_utils** (COMPLETE): Provides `is_external_artifact()`, `load_external_ref()`, `create_external_yaml()` in `src/external_refs.py`
- **chunk task_aware_narrative_cmds** (COMPLETE): Establishes the pattern for task-aware workflow artifact commands

## Risks and Open Questions

- **None identified**: The implementation closely follows the established pattern from narratives, minimizing risk. The `external_refs.py` utilities already support all artifact types including `ArtifactType.INVESTIGATION`.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
