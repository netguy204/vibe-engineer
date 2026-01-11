<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements `ve artifact promote`, a command that moves a local artifact
(chunk, narrative, investigation, or subsystem) from a project's `docs/` directory
to the task-level external artifact repository. The command is specifically for
task-level promotion when working in a multi-repo task context.

**Strategy**: Follow the established patterns from task-aware artifact commands
(`create_task_chunk`, `create_task_narrative`, etc.) but operate in reverse—instead
of creating an artifact in the external repo and references in projects, we move
an existing local artifact to the external repo and replace it with an external
reference.

**Key patterns to reuse**:
- Task context detection via `is_task_directory()` and `load_task_config()`
- Artifact type detection via `detect_artifact_type_from_path()`
- External reference creation via `create_external_yaml()`
- Artifact ordering via `ArtifactIndex` for causal chain management
- Frontmatter update via `update_frontmatter_field()`

**Test-driven approach**: Following TESTING_PHILOSOPHY.md, write failing tests first
for the core behaviors, then implement. Focus on semantic assertions (files exist
in expected locations, frontmatter contains expected values) rather than structural
assertions.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow_artifacts
  subsystem for external reference patterns, artifact type detection, causal ordering,
  and frontmatter schemas. The subsystem already defines:
  - `ExternalArtifactRef` model for external.yaml files
  - `ArtifactIndex` for causal ordering and tip detection
  - `create_external_yaml()` for creating external references
  - `detect_artifact_type_from_path()` for inferring artifact type
  - `ARTIFACT_DIR_NAME` and `ARTIFACT_MAIN_FILE` constants

  This chunk will add a new function (`promote_artifact()`) following the established
  patterns in `task_utils.py`. No deviations expected—the subsystem is STABLE and
  provides all necessary building blocks.

## Sequence

### Step 1: Write failing tests for promote_artifact core function

Create `tests/test_artifact_promote.py` with tests covering the core promotion logic:

1. **Happy path**: Promotes a local investigation to external repo
   - Source artifact directory is copied to external repo's docs/<type>/
   - Source directory is cleared and external.yaml is created
   - External.yaml contains correct artifact_type, artifact_id, repo, pinned, created_after
   - Promoted artifact's frontmatter has updated created_after (external repo tips)
   - Promoted artifact's frontmatter has dependents list containing source project

2. **--name flag**: Renames artifact during promotion
   - Artifact copied to external repo with new name
   - External.yaml references the new name as artifact_id

3. **Collision detection**: Errors when destination exists
   - Returns error if artifact with same name exists in external repo
   - Error message is user-friendly

4. **Already-external rejection**: Errors for external references
   - Returns error if artifact is already an external reference (has external.yaml, no main doc)
   - Error message explains the artifact is already external

5. **Task context detection**: Errors when not in task context
   - Returns error with clear message if not in task directory

6. **created_after preservation**: External.yaml preserves original causal position
   - External.yaml's created_after matches the original artifact's created_after field

Location: tests/test_artifact_promote.py

### Step 2: Implement TaskPromoteError and promote_artifact function

Add to `src/task_utils.py`:

1. **TaskPromoteError** exception class for user-friendly error messages

2. **promote_artifact()** function that:
   - Validates the artifact path exists and contains a main document
   - Detects artifact type from path
   - Walks up to find task directory (`.ve-task.yaml`)
   - Identifies source project from task config's projects list
   - Checks for collision in external repo (error if exists, unless --name provides alternate)
   - Copies artifact directory to external repo's docs/<type>/<dest-name>/
   - Gets current tips from external repo for the artifact's created_after
   - Updates promoted artifact's frontmatter: sets created_after to external tips, adds source project to dependents
   - Saves the original artifact's created_after field before clearing
   - Clears source directory and creates external.yaml with the saved created_after

Parameters:
- artifact_path: Path to local artifact directory
- new_name: Optional new name for destination (--name flag value)

Returns:
- Dict with external_artifact_path, external_yaml_path

Location: src/task_utils.py

### Step 3: Implement find_task_directory helper

Add helper function to walk up from a path to find the task directory:

```python
def find_task_directory(start_path: Path) -> Path | None:
    """Walk up from start_path to find directory containing .ve-task.yaml."""
```

This is needed because promote is called with an artifact path that may be
nested inside a project within the task directory.

Location: src/task_utils.py

### Step 4: Implement identify_source_project helper

Add helper to identify which project in task config contains the artifact:

```python
def identify_source_project(task_dir: Path, artifact_path: Path, config: TaskConfig) -> str:
    """Determine which project (org/repo format) contains the artifact."""
```

Matches artifact_path against each project in config.projects by resolving
project paths and checking if artifact_path is within that project.

Location: src/task_utils.py

### Step 5: Implement add_dependents helper for all artifact types

Generalize the existing `add_dependents_to_chunk/narrative/investigation/subsystem`
helpers into a single generic helper:

```python
def add_dependents_to_artifact(
    artifact_path: Path,
    artifact_type: ArtifactType,
    dependents: list[dict],
) -> None:
```

Uses `ARTIFACT_MAIN_FILE` to determine the correct file to update.

Location: src/task_utils.py

### Step 6: Write failing CLI tests

Add CLI tests to `tests/test_artifact_promote.py`:

1. **CLI exists**: `ve artifact promote <path>` command exists
2. **Validates path exists**: Errors for non-existent path
3. **--name flag works**: Renames during promotion
4. **Output format**: Reports success with paths
5. **No git commands**: Verifies no auto-commit (filesystem changes only)

### Step 7: Implement CLI command

Add `artifact` command group and `promote` subcommand to `src/ve.py`:

```python
@cli.group()
def artifact():
    """Artifact management commands."""
    pass

@artifact.command()
@click.argument("artifact_path", type=click.Path(exists=True, path_type=pathlib.Path))
@click.option("--name", "new_name", type=str, help="New name for artifact in destination")
def promote(artifact_path, new_name):
    """Promote a local artifact to the task-level external repository."""
```

The CLI:
- Validates artifact_path points to a valid artifact directory
- Calls promote_artifact() from task_utils
- Reports created paths to user
- Does NOT run any git commands

Location: src/ve.py

### Step 8: Run tests and fix any issues

Execute the full test suite to verify:
- All new tests pass
- No regressions in existing tests
- Tests cover the success criteria from GOAL.md

```bash
uv run pytest tests/test_artifact_promote.py -v
uv run pytest tests/ -v
```

---

**BACKREFERENCE COMMENTS**

Add chunk backreferences at function level:
```python
# Chunk: docs/chunks/artifact_promote - Artifact promotion to external repo
```

## Dependencies

No new external libraries required. All dependencies are already in place:
- `shutil` from Python standard library for directory copy operations
- Existing task_utils.py infrastructure for task context detection
- Existing external_refs.py utilities for external reference handling
- Existing artifact_ordering.py for causal ordering

## Risks and Open Questions

1. **Filesystem atomicity**: The promote operation involves multiple steps (copy,
   update frontmatter, clear source, create external.yaml). If interrupted mid-way,
   the artifact could be in an inconsistent state. Mitigation: Document that users
   should use git to recover if interrupted; the command does not auto-commit so
   partial changes are visible.

2. **Collision with --name**: If `--name` is provided but an artifact with that name
   already exists in the external repo, we error. This is intentional—the user should
   pick a unique name or handle the collision manually.

3. **Existing external.yaml with content**: When clearing the source directory, we
   preserve only the external.yaml pattern. If there are other files (e.g., notes,
   scratch files), they will be deleted. This matches the existing pattern where
   external artifact directories contain only external.yaml.

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