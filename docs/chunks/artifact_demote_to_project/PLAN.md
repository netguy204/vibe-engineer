

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Demote is the inverse of `promote_artifact()` in `src/task/promote.py`. Where
promote moves a local artifact to the external repo and leaves an `external.yaml`
pointer, demote moves an external artifact back into the single project that
references it, replacing the `external.yaml` with the actual files.

**Strategy:**

1. **Core engine** (`src/task/demote.py`): A `demote_artifact()` function that
   reverses the promote flow, plus a `scan_demotable_artifacts()` function for
   `--auto` mode.
2. **CLI surface** (`src/cli/task.py`): `ve task demote <artifact>` and
   `ve task demote --auto [--apply]`.
3. **Chunk-complete hook** (`src/cli/chunk.py`): Remove the task-context gate
   from `complete_chunk()` and add auto-demotion logic after status update.
4. **TDD**: Write failing tests first per TESTING_PHILOSOPHY.md, then implement.

**Existing code to reuse:**
- `remove_artifact_from_external()` — handles external.yaml deletion, empty
  directory cleanup, and dependent entry removal
- `identify_source_project()` — resolves which project owns an artifact path
- `normalize_artifact_path()` — flexible artifact path input
- `load_task_config()`, `find_task_directory()`, `resolve_repo_directory()` —
  task context resolution
- `create_external_yaml()` pattern (inverse: reading external.yaml to find source)

**Architecture decisions referenced:**
- DEC-006: External references resolve to HEAD — demote copies current HEAD
  content, no pinned SHA handling needed
- DEC-009: ArtifactManager Template Method — demote works across all artifact
  types using the same algorithm

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow
  artifacts subsystem — it follows the same artifact lifecycle patterns
  (frontmatter parsing, status transitions, directory conventions) established
  by promote/copy-external/remove-external. Demote is a new operation in this
  subsystem's surface area.
- **docs/subsystems/cross_repo_operations**: This chunk IMPLEMENTS a new
  cross-repo operation (external → local) following the patterns established
  by promote (local → external) and copy-external.

## Sequence

### Step 1: Add `TaskDemoteError` exception

Add `TaskDemoteError` to the exception hierarchy in `src/task/exceptions.py`,
following the pattern of `TaskPromoteError`. Export it from `src/task/__init__.py`.

Location: `src/task/exceptions.py`, `src/task/__init__.py`

### Step 2: Write failing tests for single-artifact demote

Create `tests/test_task_demote.py` with tests for the core `demote_artifact()`
function. Use existing test helpers from `conftest.py` for task directory setup.

Tests to write (all should fail initially):

1. **Happy path**: Set up an external artifact in a single project — call
   `demote_artifact()` — verify the artifact files (GOAL.md/PLAN.md or
   OVERVIEW.md) are copied from external repo into the project's local
   `docs/chunks/<name>/` directory, the `external.yaml` is removed, and the
   dependent entry is removed from the external artifact's frontmatter.

2. **Multi-project skip**: Set up an external artifact referenced by two
   projects (two dependent entries) — call `demote_artifact()` — verify it
   raises `TaskDemoteError` because the artifact has multiple dependents.

3. **Already local**: Call `demote_artifact()` on an artifact that has no
   `external.yaml` (already local) — verify it raises `TaskDemoteError`.

4. **All artifact types**: Verify demote works for chunks (GOAL.md + PLAN.md),
   investigations (OVERVIEW.md), narratives (OVERVIEW.md), and subsystems
   (OVERVIEW.md).

5. **Preserves frontmatter**: After demote, the local artifact retains its
   original frontmatter (status, code_paths, etc.) from the external repo copy.

Location: `tests/test_task_demote.py`

### Step 3: Implement `demote_artifact()`

Create `src/task/demote.py` with the core demote function.

```python
def demote_artifact(
    task_dir: Path,
    artifact_path: str,
    target_project: str | None = None,
) -> dict:
```

**Algorithm** (inverse of `promote_artifact()`):

1. Load task config via `load_task_config(task_dir)`.
2. Resolve external repo path via `resolve_repo_directory()`.
3. Normalize the artifact path via `normalize_artifact_path()` to get
   `(artifact_type, artifact_id)`.
4. Verify the artifact exists in the external repo.
5. Read the artifact's frontmatter to get the `dependents` list.
6. Validate exactly one dependent exists (or `target_project` is specified to
   pick one). If multiple dependents and no target specified, raise
   `TaskDemoteError` with a message listing the dependent projects.
7. Resolve the target project directory.
8. Verify the target project has an `external.yaml` for this artifact.
9. Copy the artifact directory contents from external repo to the target
   project's local artifact directory (e.g., `docs/chunks/<name>/`), replacing
   the `external.yaml` with the actual files.
10. Call `remove_artifact_from_external()` to clean up the `external.yaml` and
    dependent entry. (This function already handles both steps.)
11. If no other dependents remain on the external artifact, optionally clean up
    the external repo copy (or warn that it's orphaned).

**Return value:**
```python
{
    "demoted_artifact": str,        # artifact_id
    "artifact_type": str,           # e.g., "chunk"
    "target_project": str,          # org/repo
    "local_path": Path,             # path in project
    "external_cleaned": bool,       # whether external copy was cleaned
}
```

Export `demote_artifact` from `src/task/__init__.py`.

Location: `src/task/demote.py`, `src/task/__init__.py`

### Step 4: Write failing tests for `scan_demotable_artifacts()`

Add tests to `tests/test_task_demote.py` for the auto-scan logic:

1. **Finds single-project artifacts**: Set up 3 external artifacts — one with 1
   dependent (demotable), one with 2 dependents (not demotable), one with 0
   dependents (orphaned, not demotable). Verify the scanner returns only the
   single-dependent artifact.

2. **Empty result**: All external artifacts have multiple dependents — verify
   scanner returns empty list.

3. **Code path heuristic**: An artifact whose `code_paths` all resolve to one
   project and whose `code_references` have no `::` cross-project qualifiers is
   flagged as demotable even if dependents haven't been fully resolved.

Location: `tests/test_task_demote.py`

### Step 5: Implement `scan_demotable_artifacts()`

```python
def scan_demotable_artifacts(
    task_dir: Path,
) -> list[dict]:
```

**Algorithm:**

1. Load task config.
2. Resolve external repo path.
3. Iterate over all artifacts in the external repo (all types: chunks,
   investigations, narratives, subsystems) using the artifact managers.
4. For each artifact, read frontmatter and check `dependents`:
   - If exactly 1 dependent → candidate for demotion.
   - If 0 dependents → orphaned (report but don't include as demotable).
   - If 2+ dependents → skip.
5. For candidates, also check `code_paths` and `code_references`:
   - All `code_paths` within one project? No `::` qualifiers in
     `code_references`? → confirmed single-project.
6. Return list of dicts with `artifact_id`, `artifact_type`,
   `target_project`, and `reason`.

Location: `src/task/demote.py`

### Step 6: Write failing tests for CLI commands

Add CLI integration tests to `tests/test_task_demote.py`:

1. **`ve task demote <artifact>`**: Invokes `demote_artifact()`, prints
   confirmation message with artifact name and target project.

2. **`ve task demote --auto`**: Dry-run mode — prints table of demotable
   artifacts without modifying anything. Exit code 0.

3. **`ve task demote --auto --apply`**: Calls `demote_artifact()` for each
   candidate, prints summary of what was demoted.

4. **Error cases**: Missing task context, artifact not found, multi-project
   artifact without `--force`.

Location: `tests/test_task_demote.py`

### Step 7: Implement CLI commands

Add `demote` subcommand to `src/cli/task.py`:

```python
@task.command()
@click.argument("artifact", required=False)
@click.option("--auto", is_flag=True, help="Scan and demote all single-project artifacts")
@click.option("--apply", is_flag=True, help="Apply auto-demotion (default is dry-run)")
@click.option("--cwd", type=click.Path(exists=True), default=".")
def demote(artifact, auto, apply, cwd):
```

**Behavior:**

- If `artifact` is provided: call `demote_artifact()` for that specific
  artifact, print result.
- If `--auto` without `--apply`: call `scan_demotable_artifacts()`, print
  table of candidates (artifact, type, target project, reason).
- If `--auto --apply`: call `scan_demotable_artifacts()`, then
  `demote_artifact()` for each, print summary.
- If neither `artifact` nor `--auto`: print help/error.

Location: `src/cli/task.py`

### Step 8: Write failing tests for chunk-complete in task context

Add tests to `tests/test_task_demote.py` (or a new
`tests/test_chunk_complete_task.py`):

1. **Auto-demote on complete**: In task context, complete an external chunk
   whose artifact has exactly 1 dependent. Verify the chunk is automatically
   demoted to the local project after status update.

2. **No auto-demote for multi-project**: Complete an external chunk with 2+
   dependents. Verify it stays external and a message is logged.

3. **Non-task context unchanged**: Completing a chunk outside task context
   behaves exactly as before (no demotion logic triggered).

Location: `tests/test_task_demote.py` or `tests/test_chunk_complete_task.py`

### Step 9: Enable chunk-complete in task context with auto-demotion

Modify `src/cli/chunk.py`'s `complete_chunk()` function:

1. Remove the early-exit gate that rejects task directories (`is_task_directory`
   check that currently raises an error).
2. After the existing status update to ACTIVE, add a task-context check:
   - If `check_task_project_context(project_dir)` returns a context:
     - Load the chunk's `external.yaml` to get the external artifact reference.
     - Read the external artifact's `dependents` list.
     - If exactly 1 dependent (this project), call `demote_artifact()`.
     - Print a message: "Auto-demoted {chunk} to local project (single-project artifact)."
     - If multiple dependents, print info: "Chunk {chunk} references {n} projects; keeping as external."
3. The chunk complete flow itself (status update, code_references, etc.) should
   work identically whether the chunk is local or external — only the
   post-completion demotion step is new.

Location: `src/cli/chunk.py`

### Step 10: Update exports and backreferences

1. Export `demote_artifact`, `scan_demotable_artifacts`, and `TaskDemoteError`
   from `src/task/__init__.py`.
2. Add backreference comments to `src/task/demote.py`:
   ```python
   # Chunk: docs/chunks/artifact_demote_to_project - Demote external artifacts to project-local
   # Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact manager pattern
   ```
3. Update GOAL.md `code_paths` if any additional files were touched.

Location: `src/task/__init__.py`, `src/task/demote.py`

## Dependencies

No chunk dependencies — all required infrastructure exists:
- `promote_artifact()` and `remove_artifact_from_external()` are implemented
- `normalize_artifact_path()` and task config helpers are available
- Test fixtures for task directory setup exist in `conftest.py`

## Risks and Open Questions

- **Partial demotion failure**: If the copy from external repo succeeds but the
  cleanup (external.yaml removal, dependent entry removal) fails, the artifact
  exists in two places. Mitigation: perform copy first, then cleanup. If cleanup
  fails, the worst case is a stale `external.yaml` alongside the real files —
  recoverable manually.

- **`created_after` restoration**: When an artifact was promoted, its
  `created_after` was updated to external repo tips. When demoting back, should
  we restore the original `created_after` (preserved in the `external.yaml`)?
  Plan: yes, restore from external.yaml's `created_after` field if present.

- **Chunk-complete in task context scope**: The GOAL says "currently unsupported
  — this chunk should also enable it." Enabling the full chunk-complete flow in
  task context may surface issues beyond just demotion (e.g., code_references
  resolution across repos). Plan: enable it minimally — the core status update
  and demotion — and document any broader issues as future work.

- **External repo cleanup**: After demotion, should the artifact directory be
  removed from the external repo? If other artifacts reference it (e.g., in
  `created_after`), removal could break causal chains. Plan: leave the external
  copy in place by default but warn that it's orphaned (0 dependents). Add a
  `--clean-external` flag for explicit cleanup.

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