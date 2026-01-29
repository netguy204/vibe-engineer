<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The fix requires modifying the `list_chunks` function in `src/ve.py` to detect external
chunk references before attempting to parse frontmatter. The current code flow is:

1. `chunks.list_chunks()` returns chunk directory names (already works - includes external)
2. `chunks.parse_chunk_frontmatter_with_errors()` tries to read GOAL.md (fails for external)
3. Output shows `[PARSE ERROR: Chunk 'X' not found]`

The solution is to check `is_external_artifact()` before attempting frontmatter parsing.
For external chunks, we'll display `[EXTERNAL: org/repo]` status instead.

**Patterns used:**
- The `is_external_artifact()` function from `external_refs.py` detects external chunks
- The `load_external_ref()` function from `external_refs.py` loads the `external.yaml` content
- The `artifact_ordering.py` module already uses "EXTERNAL" as a pseudo-status for tip detection

**Test approach (TDD):**
Following docs/trunk/TESTING_PHILOSOPHY.md, write the failing test first that creates an
external chunk reference and expects `[EXTERNAL:` in the output instead of `[PARSE ERROR:`.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk USES the workflow artifact
  lifecycle subsystem. The `is_external_artifact()` and `load_external_ref()` functions are
  part of this subsystem's external reference utilities.

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): This chunk USES the cross-repo
  operations subsystem. The `external_refs.py` module is a core part of this subsystem.

## Sequence

### Step 1: Write failing test for external chunk listing

Create a test in `tests/test_chunk_list.py` that:
1. Creates a chunk directory with only `external.yaml` (no GOAL.md)
2. Runs `ve chunk list`
3. Asserts that the output shows `[EXTERNAL:` instead of `[PARSE ERROR:`
4. Verifies the external repo is shown in the status

Location: `tests/test_chunk_list.py`

Test will fail initially because the code doesn't handle external chunks.

### Step 2: Implement external chunk detection in list_chunks

Modify the `list_chunks` function in `src/ve.py` to:
1. Import `is_external_artifact`, `load_external_ref` from `external_refs`
2. Before calling `parse_chunk_frontmatter_with_errors()`, check if the chunk
   is an external reference using `is_external_artifact()`
3. If external, load the `external.yaml` and display `[EXTERNAL: {repo}]` status
4. Skip the frontmatter parsing for external chunks

Location: `src/ve.py` lines ~250-261

### Step 3: Verify test passes and add edge case tests

Run the test from Step 1 to verify it passes. Add additional tests:
1. Test mixed local and external chunks display correctly
2. Test external chunks participate in causal ordering (already works per `artifact_ordering.py`)
3. Test `--latest` flag behavior with external chunks

Location: `tests/test_chunk_list.py`

### Step 4: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the actual files modified:
- `src/ve.py`
- `tests/test_chunk_list.py`

---

**BACKREFERENCE COMMENTS**

Add the following backreference to the modified code in `src/ve.py`:

```python
# Chunk: docs/chunks/chunklist_external_status - External chunk list handling
```

## Dependencies

No external dependencies. All required utilities already exist:
- `external_refs.is_external_artifact()` - detects external artifacts
- `external_refs.load_external_ref()` - loads external.yaml content
- `models.ArtifactType.CHUNK` - artifact type enum

## Risks and Open Questions

- **Tip indicator for external chunks**: The `artifact_ordering.py` module already handles
  external chunks for tip detection (assigns "EXTERNAL" pseudo-status which is always tip-eligible).
  Need to verify the tip indicator (`*`) still displays correctly for external chunks.

- **--latest flag with external chunks**: The `--latest` flag looks for IMPLEMENTING status.
  External chunks don't have GOAL.md, so they can't be IMPLEMENTING. This is probably
  correct behavior (external references are typically to ACTIVE chunks), but worth verifying.

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