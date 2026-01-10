<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Replace sequence-number-based ordering in all list commands with causal ordering
via `ArtifactIndex`. The four list commands to update are:

1. `ve chunk list` (src/ve.py:162-194)
2. `ve subsystem list` (src/ve.py:398-415)
3. `ve investigation list` (src/ve.py:580-622)
4. `ve narrative list` - **currently missing, must be added**

Each command will:
1. Create an `ArtifactIndex` instance
2. Call `get_ordered(artifact_type)` to get causal order (oldest first)
3. Reverse the list to display newest first (matching current chunk list behavior)
4. Call `find_tips(artifact_type)` to identify tip artifacts
5. Display a tip indicator (e.g., `*`) for artifacts that are tips

**Backward compatibility**: The `ArtifactIndex` topological sort already handles
the fallback case implicitly - when all artifacts have empty `created_after`,
they become roots and are sorted alphabetically. Since directory names start with
`NNNN-`, alphabetical order equals sequence number order. This means the current
repository (where `created_after` contains all predecessors, creating a flat graph
where everything is a root) will naturally fall back to sequence ordering.

The `Chunks.list_chunks()` method that currently returns `list[tuple[int, str]]`
sorted by sequence number will be updated to use `ArtifactIndex` internally.
Similar patterns for subsystems and investigations.

## Subsystem Considerations

- **docs/subsystems/0002-workflow_artifacts** (DOCUMENTED): This chunk IMPLEMENTS
  causal ordering for artifact listings. Uses `ArtifactIndex` from
  `src/artifact_ordering.py` which was added by chunk 0038.

## Sequence

### Step 1: Update `Chunks.list_chunks()` to use ArtifactIndex

Modify `src/chunks.py` `Chunks.list_chunks()` method to use `ArtifactIndex` instead
of parsing sequence numbers from directory names.

**Current behavior**: Returns `list[tuple[int, str]]` sorted by sequence number
descending. The `int` is the sequence number extracted via regex `r"^(\d{4})-"`.

**New behavior**: Returns `list[str]` in causal order (newest first) from
`ArtifactIndex.get_ordered()` reversed. Remove the sequence number tuple since
it's no longer meaningful for ordering.

**Changes required**:
- Update `list_chunks()` signature to return `list[str]`
- Use `ArtifactIndex(self.project_root).get_ordered(ArtifactType.CHUNK)`
- Reverse the list to get newest first
- Update callers in `src/ve.py` that expect `tuple[int, str]`

**Existing tests to update**: `tests/test_chunk_list.py`
- `test_multiple_chunks_reverse_order` - update to not rely on sequence numbers

Location: `src/chunks.py`

### Step 2: Add tip indicator to `ve chunk list` output

Update the `list_chunks` command in `src/ve.py` to display a tip indicator for
artifacts with no dependents.

**Changes required**:
- Get tips from `ArtifactIndex.find_tips(ArtifactType.CHUNK)`
- Display `*` after the status for tip artifacts
- Example output: `docs/chunks/0041-artifact_list_ordering [IMPLEMENTING] *`

**Tests to add**:
- Test that tip indicator appears for artifacts with no dependents
- Test that non-tip artifacts don't have the indicator

Location: `src/ve.py`

### Step 3: Update `ve subsystem list` to use ArtifactIndex

Modify the `list_subsystems` command in `src/ve.py` to use `ArtifactIndex` for
ordering instead of `sorted()`.

**Current behavior**: Uses `sorted(subsystem_list)` which orders by directory name
(ascending, oldest first).

**New behavior**: Use `ArtifactIndex.get_ordered(ArtifactType.SUBSYSTEM)` reversed
for newest first. Display tip indicators.

**Changes required**:
- Import `ArtifactIndex` and `ArtifactType`
- Replace `sorted(subsystem_list)` with `ArtifactIndex` call
- Add tip indicator display

**Tests to update**: `tests/test_subsystem_list.py`

Location: `src/ve.py`

### Step 4: Update `ve investigation list` to use ArtifactIndex

Modify the `list_investigations` command in `src/ve.py` to use `ArtifactIndex`.

**Current behavior**: Uses `sorted(investigation_list)` for ascending order.

**New behavior**: Use `ArtifactIndex.get_ordered(ArtifactType.INVESTIGATION)`
reversed for newest first. Display tip indicators.

**Changes required**:
- Replace `sorted()` with `ArtifactIndex` call
- Add tip indicator display
- Maintain `--state` filter functionality (filter after ordering)

**Tests to update**: `tests/test_investigation_list.py`

Location: `src/ve.py`

### Step 5: Add `ve narrative list` command

Add a new `list` subcommand to the `narrative` command group.

**Implementation**:
- Follow the pattern of `list_subsystems` and `list_investigations`
- Use `ArtifactIndex.get_ordered(ArtifactType.NARRATIVE)` reversed
- Display tip indicators
- Parse frontmatter for status using existing `Narratives.parse_narrative_frontmatter()`
- Exit with code 1 if no narratives found

**Output format**: `docs/narratives/{name} [{status}] *`

**Tests to add**: `tests/test_narrative_list.py`
- Test empty project exits with error
- Test single narrative outputs path with status
- Test multiple narratives in correct order
- Test tip indicator display

Location: `src/ve.py`

### Step 6: Add backward compatibility test

Add a test to `tests/test_artifact_ordering.py` verifying that mixed scenarios
work correctly:
- Some artifacts with `created_after` populated
- Some artifacts without `created_after` (simulating pre-migration state)
- Verify ordering falls back to sequence number for artifacts without causal data

This validates that the current repository (chunks 0001-0036 without `created_after`)
will continue to order correctly.

### Step 7: Verify all tests pass

Run the full test suite to ensure no regressions.

```bash
uv run pytest tests/
```

Fix any failing tests discovered during the run.

## Dependencies

- **0038-artifact_ordering_index**: Provides `ArtifactIndex` class
- **0039-populate_created_after**: Ensures new artifacts have `created_after` populated
- **0037-created_after_field**: Provides the `created_after` field in frontmatter models

## Risks and Open Questions

1. **Task directory mode**: The `ve chunk list` command has special handling for
   task directories (cross-repo mode) via `_list_task_chunks()`. This code path
   may need similar updates or may work differently. Need to verify during
   implementation.

2. **Signature change impact**: Changing `list_chunks()` from `list[tuple[int, str]]`
   to `list[str]` may break other callers not identified during planning. Will
   need to grep for usages.

3. **Tip indicator format**: Using `*` as the tip indicator - confirm this is
   visible and unambiguous in terminal output.

4. **Backward compatibility verification**: Chunks 0001-0036 lack `created_after`
   field entirely. The fallback relies on alphabetical sorting of roots matching
   sequence order. Should add a test verifying mixed scenarios (some with
   `created_after`, some without) produce correct ordering.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->