<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The `ve validate` command runs `IntegrityValidator.validate()` which iterates over all chunks via `self.chunks.enumerate_chunks()`. For each chunk, it calls `parse_chunk_frontmatter(chunk_name)` which reads `GOAL.md`. External chunks (directories with `external.yaml` but no `GOAL.md`) cause frontmatter parsing to fail because there's no `GOAL.md` to parse.

**Strategy:** Detect external chunks during validation and skip them with a clear log message. External chunks are pointers to canonical artifacts in other repositories—validating them would require dereferencing (network access, repo cache), which is out of scope for a local integrity check. The canonical artifact's integrity is validated in its home repository.

**Existing code to leverage:**
- `is_external_artifact(path, ArtifactType.CHUNK)` from `external_refs.py` already detects external chunks
- `ArtifactType.CHUNK` constant from `models.py`
- The `IntegrityResult` dataclass already tracks `chunks_scanned` — we'll add `external_chunks_skipped` for visibility

**Design decision:** We choose to skip external chunks rather than dereference them because:
1. DEC-006 establishes that external refs resolve to HEAD, which would require network access
2. The canonical artifact is already validated in its home repository
3. Adding dereferencing logic to `ve validate` would significantly increase complexity and runtime

**Testing approach:** Follow TDD per TESTING_PHILOSOPHY.md:
1. Write failing tests first for external chunk scenarios
2. Implement the fix
3. Verify tests pass

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the `is_external_artifact()` utility from the external reference infrastructure to detect external chunks
- **docs/subsystems/cross_repo_operations** (DOCUMENTED): This chunk USES the external artifact detection pattern established by this subsystem but does not extend it

## Sequence

### Step 1: Write failing tests for external chunk validation scenarios

Create tests in `tests/test_integrity.py` that verify:
1. A project with only external chunks passes validation (no errors)
2. A project with mixed local and external chunks validates correctly (only local chunks validated)
3. External chunks are reported in validation output (skipped count)
4. The CLI shows "Skipping external chunk: {name}" message with `--verbose`

Location: `tests/test_integrity.py` (new test class `TestIntegrityValidatorExternalChunks`)

**Helper needed:** Create a `write_external_chunk()` helper that writes an `external.yaml` file for testing.

### Step 2: Add `external_chunks_skipped` field to IntegrityResult

Extend the `IntegrityResult` dataclass to track how many external chunks were skipped during validation:

```python
@dataclass
class IntegrityResult:
    # ... existing fields ...
    external_chunks_skipped: int = 0  # NEW
```

Location: `src/integrity.py`

### Step 3: Modify IntegrityValidator to detect and skip external chunks

In `IntegrityValidator._build_artifact_index()` and `IntegrityValidator.validate()`:

1. Import `is_external_artifact` from `external_refs.py` and `ArtifactType` from `models.py`
2. When building `_chunk_names`, detect and separate external chunks:
   ```python
   external_chunks: set[str] = set()
   local_chunks: set[str] = set()
   for chunk_name in self.chunks.enumerate_chunks():
       chunk_path = self.chunk_dir / chunk_name
       if is_external_artifact(chunk_path, ArtifactType.CHUNK):
           external_chunks.add(chunk_name)
       else:
           local_chunks.add(chunk_name)
   self._chunk_names = local_chunks
   self._external_chunk_names = external_chunks
   ```
3. Update `validate()` to track `external_chunks_skipped` in the result

Location: `src/integrity.py`

### Step 4: Update CLI to show external chunk info

In `src/ve.py`, update the `validate` command to:
1. Show external chunks skipped in verbose output: `External chunks skipped: N`
2. With `--verbose`, list each skipped chunk: `Skipping external chunk: {name}`

Location: `src/ve.py#validate` (the top-level `ve validate` command, ~line 159)

### Step 5: Run tests and verify all pass

Run `uv run pytest tests/test_integrity.py -v` to verify:
- All new tests pass
- All existing tests still pass
- No regressions

### Step 6: Update GOAL.md code_paths

Add the files touched to the chunk's `code_paths` frontmatter field.

## Dependencies

No external dependencies. All required utilities already exist:
- `is_external_artifact()` in `src/external_refs.py`
- `ArtifactType.CHUNK` in `src/models.py`

## Risks and Open Questions

1. **Bidirectional consistency for external chunks**: The `_validate_chunk_outbound` method checks bidirectional consistency (e.g., "chunk references narrative but narrative doesn't list chunk"). For external chunks, we skip this validation entirely. This is acceptable because the canonical artifact's bidirectional consistency is validated in its home repository.

2. **Code backreferences to external chunks**: Code in a project repo may have `# Chunk: docs/chunks/external_feature` backreferences pointing to external chunks. These should still be validated as valid because the external chunk directory exists locally (with `external.yaml`). Need to verify the code backref validation only checks directory existence, not GOAL.md existence.

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