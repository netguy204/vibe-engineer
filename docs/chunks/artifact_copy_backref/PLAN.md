<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extends `copy_artifact_as_external()` in `src/task_utils.py` to update the
source artifact's `dependents` field after successfully creating the `external.yaml`
in the target project. This implements the "back-reference" that makes the relationship
bidirectional.

**Build on:**
- `add_dependents_to_artifact()` in `task_utils.py` - already handles updating
  frontmatter `dependents` field for any artifact type
- `ARTIFACT_MAIN_FILE` from `external_refs.py` - maps artifact types to main files
  (GOAL.md for chunks, OVERVIEW.md for others)
- Existing pattern in `promote_artifact()` - already updates source artifact's
  `dependents` field

**Key insight**: The `add_dependents_to_artifact()` function already exists and can
update the `dependents` field for any artifact type. We need to:
1. Build the dependent entry with correct fields (`artifact_type`, `artifact_id`, `repo`, `pinned`)
2. Handle preservation of existing dependents (append, not overwrite)
3. Handle idempotency (don't duplicate entries on re-run)

**Strategy:**
1. Create a helper function to append a dependent entry preserving existing entries
2. Call this helper after creating `external.yaml` in `copy_artifact_as_external()`
3. Update tests to verify back-reference creation

Per DEC-005, no git operations are prescribed.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow artifacts
  subsystem patterns for:
  - External artifact references (`ExternalArtifactRef` model in `models.py`)
  - Artifact main file mapping (`ARTIFACT_MAIN_FILE` in `external_refs.py`)
  - Dependent update patterns (`add_dependents_to_artifact()` in `task_utils.py`)

  The subsystem is STABLE, so we follow its patterns exactly.

## Sequence

### Step 1: Write failing tests for back-reference creation

Add tests to `tests/test_artifact_copy_external.py` that verify the back-reference
behavior:

1. **test_back_reference_created_on_copy** - After `copy_artifact_as_external()`,
   verify the source artifact's frontmatter contains a `dependents` entry with:
   - `artifact_type`: The artifact type being copied
   - `artifact_id`: The destination name in target project
   - `repo`: The target project identifier (org/repo format)
   - `pinned`: The SHA at which the copy was made

2. **test_existing_dependents_preserved** - Create source artifact with existing
   `dependents` entries, run copy, verify old entries preserved alongside new entry

3. **test_idempotent_copy_no_duplicates** - Run copy twice with same params, verify
   only one dependent entry exists (no duplicates)

4. **test_back_reference_all_artifact_types** - Verify back-reference works for
   chunks, narratives, investigations, and subsystems

Location: `tests/test_artifact_copy_external.py`

### Step 2: Create helper to append dependent preserving existing entries

Add a new helper function `append_dependent_to_artifact()` in `src/task_utils.py`:

```python
def append_dependent_to_artifact(
    artifact_path: Path,
    artifact_type: ArtifactType,
    dependent: dict,
) -> None:
    """Append a dependent entry to artifact's frontmatter, preserving existing entries.

    If an identical dependent already exists (same repo, artifact_type, artifact_id),
    it will be updated with the new pinned SHA rather than duplicated.

    Args:
        artifact_path: Path to the artifact directory.
        artifact_type: Type of artifact to determine main file.
        dependent: Dict with keys: artifact_type, artifact_id, repo, pinned
    """
```

This function:
1. Reads existing frontmatter from the artifact's main file
2. Parses existing `dependents` list (or creates empty list)
3. Checks for existing entry with same (repo, artifact_type, artifact_id)
4. If exists, updates the `pinned` field; if not, appends new entry
5. Writes updated frontmatter back

Location: `src/task_utils.py`

### Step 3: Update copy_artifact_as_external() to add back-reference

Modify `copy_artifact_as_external()` in `src/task_utils.py` to:

1. After successfully creating `external.yaml` (step 10 in current implementation)
2. Build the dependent entry with:
   - `artifact_type`: The artifact type (from step 3's normalization)
   - `artifact_id`: The destination name (dest_name from step 6)
   - `repo`: The target project (from step 5's resolution)
   - `pinned`: The SHA from step 8
3. Call `append_dependent_to_artifact()` on the source artifact in external repo
4. Return result including new `source_updated` key

Add backreference comment:
```python
# Chunk: docs/chunks/artifact_copy_backref - Back-reference update for copy-external
```

Location: `src/task_utils.py`

### Step 4: Verify all tests pass

Run tests to verify implementation:
```bash
uv run pytest tests/test_artifact_copy_external.py -v
uv run pytest tests/ -x --tb=short
```

Ensure no regressions in existing functionality.

---

**BACKREFERENCE COMMENTS**

Add at function level in `task_utils.py`:
```
# Chunk: docs/chunks/artifact_copy_backref - Append dependent with idempotency
```
for the new `append_dependent_to_artifact()` function.

Update existing `copy_artifact_as_external()` comment to add:
```
# Chunk: docs/chunks/artifact_copy_backref - Back-reference update for copy-external
```

## Dependencies

None. All required infrastructure exists:
- `copy_artifact_as_external()` in `task_utils.py` - the function to extend
- `ARTIFACT_MAIN_FILE` in `external_refs.py` - maps artifact type to main file
- `update_frontmatter_field()` in `task_utils.py` - for updating frontmatter
- `setup_task_directory()` helper in `conftest.py` - for testing

## Risks and Open Questions

- **Frontmatter parsing edge cases**: The existing `update_frontmatter_field()`
  replaces the entire field value. We need a slightly different approach to
  preserve existing dependents. The `_get_artifact_created_after()` pattern in
  `task_utils.py` shows how to read existing frontmatter fields, which we can
  adapt for reading existing dependents.

- **Matching logic for idempotency**: The unique key for a dependent entry is
  `(repo, artifact_type, artifact_id)`. When re-running copy with same params,
  we should update the `pinned` SHA rather than create a duplicate. This ensures
  the recorded SHA reflects the most recent copy operation.

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