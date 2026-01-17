<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements `ve artifact remove-external` as the inverse of `copy_artifact_as_external()`. The implementation follows the same pattern as `copy_artifact_as_external()` in `src/task_utils.py`:

1. **Create a core function** `remove_artifact_from_external()` in `src/task_utils.py` that:
   - Uses the same flexible input handling (artifact paths, project refs)
   - Loads task config and resolves paths like `copy_artifact_as_external()`
   - Deletes the external.yaml from the project's artifact directory
   - Removes the dependent entry from the artifact's frontmatter in the external repo
   - Cleans up empty directories after deletion
   - Returns metadata about what was removed

2. **Create a CLI command** `ve artifact remove-external` in `src/ve.py` that:
   - Mirrors the interface of `copy-external`
   - Accepts flexible artifact_path and target_project arguments
   - Reports success/warnings to the user

3. **Add helper function** `remove_dependent_from_artifact()` in `src/task_utils.py` as the inverse of `append_dependent_to_artifact()`:
   - Parses frontmatter, finds matching dependent entry, removes it
   - Preserves other dependents and file content

The implementation follows TDD as per `docs/trunk/TESTING_PHILOSOPHY.md`: write failing tests first (modeled on `tests/test_artifact_copy_external.py`), then implement the functions.

**Key behaviors:**
- **Idempotent**: No error if external.yaml doesn't exist
- **Orphan warning**: Warn when removing the last project link
- **Flexible input**: Accept full paths or short names for artifacts/projects
- **Comprehensive**: Removes both external.yaml AND the dependent back-reference

## Subsystem Considerations

No subsystems are relevant to this chunk. The implementation follows existing patterns in `task_utils.py` for task-aware artifact operations.

## Sequence

### Step 1: Write failing tests for core function

Create test file `tests/test_artifact_remove_external.py` with test classes modeled after `tests/test_artifact_copy_external.py`. Write tests for:

**TestRemoveArtifactFromExternalCoreFunction:**
- `test_happy_path_removes_external_yaml` - Removes external.yaml from project
- `test_removes_dependent_from_artifact_frontmatter` - Updates dependents list in external repo
- `test_idempotent_no_error_when_external_yaml_missing` - No error if already removed
- `test_cleans_up_empty_artifact_directory` - Removes empty directory after deletion
- `test_preserves_other_files_in_artifact_directory` - Doesn't delete if other files present
- `test_error_when_not_in_task_directory` - Errors outside task context
- `test_error_when_artifact_not_in_external_repo` - Errors for nonexistent artifact
- `test_error_when_project_not_in_task_config` - Errors for unknown project
- `test_removes_all_artifact_types` - Works for chunks, investigations, narratives, subsystems
- `test_flexible_path_input` - Accepts "my_chunk", "chunks/my_chunk", "docs/chunks/my_chunk"
- `test_flexible_project_input` - Accepts "proj" or "acme/proj"
- `test_warns_when_removing_last_project_link` - Returns warning flag when artifact becomes orphaned
- `test_preserves_other_dependents` - Only removes matching dependent entry

Location: `tests/test_artifact_remove_external.py`

### Step 2: Write failing tests for CLI command

Add test class to `tests/test_artifact_remove_external.py`:

**TestRemoveArtifactFromExternalCLI:**
- `test_cli_command_exists` - Help text includes remove-external
- `test_cli_happy_path` - Returns exit code 0, removes external.yaml
- `test_cli_idempotent` - Exit code 0 when external.yaml already missing
- `test_cli_error_handling` - Non-zero exit for errors
- `test_cli_warns_on_orphan` - Output includes warning when last link removed

Location: `tests/test_artifact_remove_external.py`

### Step 3: Create error class for remove-external

Add `TaskRemoveExternalError` exception class in `src/task_utils.py`, following the pattern of `TaskCopyExternalError`:

```python
# Chunk: docs/chunks/remove_external_ref - Remove external artifact error class
class TaskRemoveExternalError(Exception):
    """Error during artifact removal from external with user-friendly message."""
    pass
```

Location: `src/task_utils.py` (near `TaskCopyExternalError`)

### Step 4: Implement remove_dependent_from_artifact() helper

Create a helper function in `src/task_utils.py` as the inverse of `append_dependent_to_artifact()`:

```python
# Chunk: docs/chunks/remove_external_ref - Remove dependent from artifact frontmatter
def remove_dependent_from_artifact(
    artifact_path: Path,
    artifact_type: ArtifactType,
    repo: str,
    artifact_id: str,
) -> bool:
    """Remove a dependent entry from artifact's frontmatter.

    Args:
        artifact_path: Path to the artifact directory.
        artifact_type: Type of artifact to determine main file.
        repo: Repository reference to match (e.g., "acme/proj").
        artifact_id: Artifact ID to match (the name in the target project).

    Returns:
        True if an entry was removed, False if no matching entry found.

    Raises:
        FileNotFoundError: If main file doesn't exist in artifact_path.
    """
```

This function:
1. Reads existing frontmatter from the artifact's main file
2. Parses existing `dependents` list
3. Finds entry matching (repo, artifact_type, artifact_id)
4. Removes it if found, preserves others
5. Writes updated frontmatter back
6. Returns whether an entry was actually removed

Location: `src/task_utils.py`

### Step 5: Implement remove_artifact_from_external() core function

Create the main function in `src/task_utils.py`:

```python
# Chunk: docs/chunks/remove_external_ref - Remove artifact from external project
def remove_artifact_from_external(
    task_dir: Path,
    artifact_path: str,
    target_project: str,
) -> dict:
    """Remove an artifact's external reference from a target project.

    Inverse of copy_artifact_as_external(). Removes the external.yaml from the
    target project and updates the artifact's dependents list in the external repo.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        artifact_path: Flexible path to artifact (e.g., "docs/chunks/my_chunk",
                       "chunks/my_chunk", or just "my_chunk")
        target_project: Flexible project ref (e.g., "acme/proj" or just "proj")

    Returns:
        Dict with keys:
        - removed: bool - True if external.yaml was removed
        - dependent_removed: bool - True if dependent entry was removed from source
        - orphaned: bool - True if this was the last project link (warning)
        - directory_cleaned: bool - True if empty directory was removed

    Raises:
        TaskRemoveExternalError: If any step fails, with user-friendly message.
    """
```

Implementation steps (mirroring copy_artifact_as_external):
1. Load task config
2. Resolve external repo path
3. Normalize artifact path with external repo context
4. Verify the artifact exists in external repo
5. Resolve flexible project reference
6. Resolve target project path
7. Determine the artifact directory in target project (using the same name)
8. Check if external.yaml exists (idempotent - return early with removed=False if not)
9. Load external.yaml to get the actual artifact_id (may differ if --name was used on copy)
10. Delete external.yaml
11. Remove directory if now empty
12. Remove dependent entry from source artifact's frontmatter
13. Check if dependents list is now empty (orphan warning)
14. Return result dict

Location: `src/task_utils.py`

### Step 6: Implement CLI command

Add the CLI command in `src/ve.py`, following the pattern of `copy-external`:

```python
# Chunk: docs/chunks/remove_external_ref - Remove external artifact command
@artifact.command("remove-external")
@click.argument("artifact_path")
@click.argument("target_project")
@click.option("--cwd", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def remove_external(artifact_path, target_project, cwd):
    """Remove an external artifact reference from a target project.

    Inverse of copy-external. Removes the external.yaml from the target project
    and updates the artifact's dependents list in the external repo.

    ARTIFACT_PATH accepts flexible formats: "docs/chunks/my_chunk", "chunks/my_chunk",
    or just "my_chunk" (if unambiguous).

    TARGET_PROJECT accepts flexible formats: "acme/proj" or just "proj" (if unambiguous).
    """
```

The command:
1. Calls `remove_artifact_from_external()`
2. Reports what was removed
3. Warns if artifact is now orphaned (no project links remaining)
4. Exit code 0 for success (including idempotent no-op), non-zero for errors

Location: `src/ve.py`

### Step 7: Add imports and exports

Update `src/task_utils.py` module-level exports to include:
- `TaskRemoveExternalError`
- `remove_dependent_from_artifact`
- `remove_artifact_from_external`

Update `src/ve.py` imports to include the new function and error class.

Location: `src/task_utils.py`, `src/ve.py`

### Step 8: Verify all tests pass

Run the full test suite to verify implementation:

```bash
uv run pytest tests/test_artifact_remove_external.py -v
uv run pytest tests/ -x --tb=short
```

Ensure no regressions in existing functionality.

---

**BACKREFERENCE COMMENTS**

Add at function level in `task_utils.py`:
```python
# Chunk: docs/chunks/remove_external_ref - Remove external artifact error class
# Chunk: docs/chunks/remove_external_ref - Remove dependent from artifact frontmatter
# Chunk: docs/chunks/remove_external_ref - Remove artifact from external project
```

Add at command level in `ve.py`:
```python
# Chunk: docs/chunks/remove_external_ref - Remove external artifact command
```

## Dependencies

No new dependencies required. Uses existing infrastructure:
- `load_task_config()`, `resolve_repo_directory()`, `normalize_artifact_path()`, `resolve_project_ref()` from `task_utils.py`
- `load_external_ref()`, `ARTIFACT_DIR_NAME`, `ARTIFACT_MAIN_FILE` from `external_refs.py`
- Test helpers from `conftest.py`: `setup_task_directory()`, `make_ve_initialized_git_repo()`

## Risks and Open Questions

1. **What if the artifact directory in the target project has other files?**
   - Decision: Only delete `external.yaml`. Do NOT remove the directory if other files exist.
   - This handles the edge case where someone manually added files to the artifact directory.

2. **What if the artifact exists in external repo but has no dependents field?**
   - Decision: Treat as success (nothing to remove). The artifact was never linked or link was already removed.

3. **How to find the correct artifact name in target project?**
   - The artifact may have been copied with `--name`, so the directory name in target project may differ from the artifact_id in external repo.
   - Solution: Accept `artifact_path` that refers to the *external repo* artifact, then look for matching external.yaml files in the target project that reference that artifact_id.
   - Simpler solution: Require the directory name in target project to match. If `--name` was used during copy, the user must specify that name.

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