<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds a new `ve artifact copy-external` CLI command that creates external references to artifacts already in the external artifact repository. The implementation follows the established patterns from `artifact promote` and task-aware artifact creation.

**Build on:**
- `create_external_yaml()` from `external_refs.py` - reuse existing external.yaml creation logic
- `ArtifactIndex.find_tips()` from `artifact_ordering.py` - for causal ordering
- `load_task_config()` and `resolve_repo_directory()` from `task_utils.py` - for task context
- Test patterns from `test_artifact_promote.py` - similar testing approach

**Strategy:**
1. Add a core function `copy_artifact_as_external()` in `task_utils.py` following the pattern of `promote_artifact()`
2. Add CLI command `ve artifact copy-external` in `ve.py` following existing artifact subcommand patterns
3. Write tests using the existing `setup_task_directory()` helper from `conftest.py`

Per DEC-005, the command will not prescribe any git operations.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk USES the external reference utilities. The `create_external_yaml()` function from `external_refs.py` is part of this subsystem and provides the core functionality for creating `external.yaml` files with proper `created_after` support.

## Sequence

### Step 1: Write failing tests for the core function

Create `tests/test_artifact_copy_external.py` with tests for `copy_artifact_as_external()`:

1. **Happy path test**: Copy an artifact from external repo to a target project
   - Set up task directory with external repo containing an artifact
   - Call `copy_artifact_as_external(task_dir, "artifact_path", "target_project")`
   - Assert `external.yaml` created in target project
   - Assert `external.yaml` contains correct fields (artifact_type, artifact_id, repo, track, pinned, created_after)

2. **created_after test**: Verify causal ordering is populated
   - Create existing artifacts in target project to be tips
   - Copy external artifact
   - Assert `created_after` in the new `external.yaml` contains the tips

3. **--name test**: Verify optional renaming works
   - Copy with `new_name` parameter
   - Assert the external reference directory uses the new name

4. **Error tests**:
   - Error when not in task directory
   - Error when source artifact doesn't exist in external repo
   - Error when target project isn't in task config
   - Error when artifact already exists in target project

Location: `tests/test_artifact_copy_external.py`

### Step 2: Implement core function `copy_artifact_as_external()`

Add function to `src/task_utils.py`:

```python
def copy_artifact_as_external(
    task_dir: Path,
    artifact_path: str,  # Path relative to external repo (e.g., "docs/chunks/my_chunk")
    target_project: str,  # Project ref from task config (e.g., "acme/proj")
    new_name: str | None = None,
) -> dict:
    """Copy an artifact from external repo as an external reference in target project."""
```

Logic:
1. Load task config from `task_dir`
2. Parse `artifact_path` to extract artifact type and artifact ID
3. Resolve external repo path and verify artifact exists
4. Resolve target project path and validate it's in task config
5. Determine destination name (use `new_name` if provided, else source artifact ID)
6. Check for collision in target project
7. Get current SHA from external repo for pinned
8. Get current tips for target project's causal ordering
9. Call `create_external_yaml()` with all parameters
10. Return result dict with created path

Location: `src/task_utils.py`

### Step 3: Write failing tests for CLI command

Add CLI tests to `tests/test_artifact_copy_external.py`:

1. **Command exists test**: `ve artifact copy-external --help` returns 0
2. **Happy path CLI test**: Command creates external reference and reports success
3. **--name flag test**: CLI passes name parameter correctly
4. **Error handling tests**: CLI returns non-zero for error cases

### Step 4: Implement CLI command `ve artifact copy-external`

Add to `ve.py` under the `artifact` command group:

```python
@artifact.command("copy-external")
@click.argument("artifact_path")
@click.argument("target_project")
@click.option("--name", "new_name", type=str, help="New name for artifact in destination")
@click.option("--cwd", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def copy_external(artifact_path, target_project, new_name, cwd):
    """Copy an external artifact as a reference in a target project."""
```

Location: `src/ve.py`

### Step 5: Verify all tests pass

Run `uv run pytest tests/test_artifact_copy_external.py -v` to verify implementation.
Run `uv run pytest tests/` to ensure no regressions.

---

**BACKREFERENCE COMMENTS**

Add at function level in `task_utils.py`:
```
# Chunk: docs/chunks/copy_as_external - Copy artifact as external reference
```

Add at command level in `ve.py`:
```
# Chunk: docs/chunks/copy_as_external - Copy external artifact command
```

## Dependencies

None. All required infrastructure exists:
- `create_external_yaml()` in `external_refs.py`
- `ArtifactIndex` in `artifact_ordering.py`
- `load_task_config()`, `resolve_repo_directory()` in `task_utils.py`
- `setup_task_directory()` helper in `conftest.py`

## Risks and Open Questions

- **Artifact path format**: The first argument (`ARTIFACT_PATH`) could be interpreted as a relative path (e.g., `docs/chunks/my_chunk`) or just the artifact ID (e.g., `my_chunk`). The plan assumes relative path format which is more explicit and matches how artifacts are referenced elsewhere. During implementation, consider accepting both formats for usability.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->