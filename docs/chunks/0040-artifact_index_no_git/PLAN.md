# Implementation Plan

## Approach

The current `ArtifactIndex` uses git hash-object to detect staleness:
1. `_get_git_hash()` - gets hash of a single file
2. `_get_all_artifact_hashes()` - batches hash-object calls for all artifacts
3. `_is_index_stale()` - compares stored hashes against current hashes

This approach violates DEC-002 (git not assumed) and is unnecessary since `created_after`
is immutable after artifact creation. We only need to detect when artifacts are **added**
or **removed**, not when their contents change.

**New approach**: Replace file content hashing with directory set comparison:
1. Store the set of artifact directory names in the index (instead of hashes)
2. On access, enumerate current directories via `pathlib`
3. If the sets differ, rebuild; otherwise use cached values

This is simpler, faster (no subprocess calls), and works without git.

**Key insight**: The only way the ordering can change is if:
- A new artifact is added (detected by set membership)
- An artifact is deleted (detected by set membership)

Content changes don't affect ordering because `created_after` is immutable.

## Subsystem Considerations

- **docs/subsystems/0002-workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS
  the artifact ordering component, removing git dependency per DEC-002.

Since the subsystem is in REFACTORING status, I will ensure changes align with
the subsystem's patterns (manager class interface, index file format conventions).

## Sequence

### Step 1: Remove git hash utility functions

Delete `_get_git_hash()` and `_get_all_artifact_hashes()` functions from
`src/artifact_ordering.py`. These are no longer needed.

Also remove the `subprocess` import since it won't be used.

Location: `src/artifact_ordering.py` (lines 10, 83-153)

### Step 2: Add directory enumeration helper

Create a new helper function `_enumerate_artifacts()` that returns a set of
artifact directory names for a given artifact type directory.

```python
def _enumerate_artifacts(artifact_dir: Path, artifact_type: ArtifactType) -> set[str]:
    """Enumerate artifact directory names.

    Args:
        artifact_dir: Directory containing artifact subdirectories.
        artifact_type: Type of artifact to determine main file name.

    Returns:
        Set of artifact directory names (only includes directories that
        have the required main file, e.g., GOAL.md or OVERVIEW.md).
    """
```

This uses pure `pathlib` operations: `artifact_dir.iterdir()`, `item.is_dir()`,
and `(item / main_file).exists()`.

Location: `src/artifact_ordering.py`

### Step 3: Update index format - replace "hashes" with "directories"

Modify `_build_index_for_type()` to store `directories` (a list of directory names)
instead of `hashes`. The list format preserves JSON serialization compatibility.

Update the index data structure:
```python
return {
    "ordered": ordered,
    "tips": tips,
    "directories": sorted(artifacts),  # Was "hashes"
    "version": _INDEX_VERSION,
}
```

Bump `_INDEX_VERSION` from 1 to 2 to force rebuild of existing indexes.

Location: `src/artifact_ordering.py` (lines 299-352)

### Step 4: Update staleness check logic

Modify `_is_index_stale()` to compare directory sets instead of checking hashes:

1. Extract `directories` from stored index (instead of `hashes`)
2. Use `_enumerate_artifacts()` to get current directories
3. Compare sets: if different, index is stale

The new logic:
```python
stored_directories = set(type_index.get("directories", []))
current_directories = _enumerate_artifacts(artifact_dir, artifact_type)
return stored_directories != current_directories
```

No more hash comparison loop needed.

Location: `src/artifact_ordering.py` (`_is_index_stale` method, lines 256-297)

### Step 5: Update module docstring and class docstring

Update the module docstring to reflect the new approach (directory enumeration
instead of git-hash-based staleness).

Update the `ArtifactIndex` class docstring similarly.

Location: `src/artifact_ordering.py` (lines 1-8, 217-227)

### Step 6: Update tests - replace git_temp_dir fixture with tmp_path

Many tests use the `git_temp_dir` fixture which initializes a git repo. Replace
these with `tmp_path` (pytest built-in) for tests that don't need git.

Key changes:
- `TestArtifactIndex` tests should use `tmp_path` (proves non-git works)
- `TestArtifactIndexIntegration` tests should use `tmp_path`
- `TestPerformance` tests should use `tmp_path`
- `TestBackwardCompatibility` tests should use `tmp_path`

Location: `tests/test_artifact_ordering.py`

### Step 7: Remove or update git hash utility tests

The `TestGitHashUtilities` test class tests `_get_git_hash` and
`_get_all_artifact_hashes` which will be deleted. Remove this entire test class.

Location: `tests/test_artifact_ordering.py` (class `TestGitHashUtilities`)

### Step 8: Update test imports

Remove `_get_git_hash` and `_get_all_artifact_hashes` from the test imports.
Add `_enumerate_artifacts` to test imports if we want to unit test it.

Location: `tests/test_artifact_ordering.py` (lines 12-19)

### Step 9: Add tests for non-git directory operation

Add a new test class `TestNonGitOperation` that explicitly verifies:
- `ArtifactIndex` works in a directory that is not a git repository
- Directory enumeration correctly detects added artifacts
- Directory enumeration correctly detects deleted artifacts

```python
class TestNonGitOperation:
    """Tests that verify ArtifactIndex works without git."""

    def test_works_in_non_git_directory(self, tmp_path):
        """ArtifactIndex works in a directory that is not a git repo."""

    def test_detects_new_artifact_without_git(self, tmp_path):
        """New artifact is detected and index rebuilds without git."""

    def test_detects_deleted_artifact_without_git(self, tmp_path):
        """Deleted artifact is detected and index rebuilds without git."""
```

Location: `tests/test_artifact_ordering.py`

### Step 10: Update test_index_file_format test

The `test_index_file_format` test verifies JSON structure. Update it to check
for `directories` instead of `hashes`, and verify the version number is 2.

Location: `tests/test_artifact_ordering.py` (`test_index_file_format`)

### Step 11: Verify all tests pass

Run the full test suite to ensure:
- All existing tests pass (or are appropriately updated)
- No subprocess calls remain in artifact_ordering.py
- ArtifactIndex works correctly in non-git environments

```bash
uv run pytest tests/test_artifact_ordering.py -v
uv run pytest tests/ -v
```

## Dependencies

- **0038-artifact_ordering_index**: Parent chunk that created `ArtifactIndex`
  (must be complete - it is ACTIVE)

## Risks and Open Questions

1. **Performance impact of directory enumeration vs hash checking**: Directory
   enumeration via `pathlib` should be faster than subprocess calls to git, but
   should verify in performance tests.

2. **Index file format migration**: Bumping version to 2 will force rebuild of
   all existing indexes. This is intentional and safe since rebuild is fast.

3. **Edge case: artifact directory exists but main file is missing**: Current
   behavior treats this as "artifact doesn't exist". New approach should
   maintain this behavior (check for main file existence in enumeration).

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->