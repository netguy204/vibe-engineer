

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The bug is in `src/entity_shutdown.py` lines 510-539 (Step 7 of `run_consolidation`). The pipeline treats the LLM consolidation response as the **complete replacement** for the consolidated and core tiers: it writes the returned memories, then deletes every existing file not in the response. When the LLM returns only newly-changed memories (or nothing), all pre-existing memories are destroyed.

The fix changes Step 7 from "clear-and-rewrite" to "merge": new/updated memories from the LLM response are written, but existing files that were not mentioned in the response are **preserved**. Only memories that the LLM explicitly included (by matching title) are overwritten.

Additionally, we add a defense-in-depth pre-consolidation snapshot so that even if a future bug re-introduces destructive behavior, the previous tier state can be recovered.

The existing test `test_replaces_existing_tiers` asserts the current (broken) destructive behavior. It will be rewritten to assert the correct merge behavior. New tests verify the specific scenarios from the success criteria.

Following docs/trunk/TESTING_PHILOSOPHY.md: tests are written first (TDD), assert semantic properties (memory survival, merge correctness), and focus on boundary conditions (empty LLM response, partial updates).

## Sequence

### Step 1: Write failing tests for merge behavior

Location: `tests/test_entity_shutdown.py`

Add new test methods to the existing `TestRunConsolidation` class:

1. **`test_existing_memories_survive_when_llm_returns_empty`** — Pre-populate 3 consolidated and 2 core memories. Mock the LLM to return `{"consolidated": [], "core": [], "unconsolidated": [...]}`. Assert all 5 pre-existing memories remain on disk unchanged.

2. **`test_new_promotions_merge_into_existing_tiers`** — Pre-populate 2 consolidated and 1 core memory. Mock the LLM to return 1 new consolidated + 1 new core (different titles from existing). Assert all existing memories survive AND the 2 new ones are added (total: 3 consolidated, 2 core).

3. **`test_llm_can_update_existing_memory_by_title`** — Pre-populate a consolidated memory with title "Template system editing". Mock the LLM to return a consolidated memory with the same title but updated content/recurrence_count. Assert the memory file is updated in-place (content changed) and no other files are deleted.

4. **`test_pre_consolidation_snapshot_created`** — Pre-populate consolidated and core memories. Run consolidation. Assert a snapshot directory exists at `.entities/<name>/memories/.snapshot_pre_consolidation/` containing copies of the prior consolidated/ and core/ directories.

Run tests → all 4 should fail (confirming the bug exists).

### Step 2: Rewrite Step 7 in `run_consolidation` to merge instead of replace

Location: `src/entity_shutdown.py`, lines 510-539

Replace the current "write-then-delete" logic with merge logic:

**For each tier (consolidated, then core):**

1. Build a lookup of existing memory files on disk: `{title: Path}` by parsing each `.md` file in the tier directory.
2. For each entry in the LLM response for this tier:
   - If the title matches an existing file → **overwrite** that file (update in place by writing to the same path, or unlink + write_memory)
   - If the title is new → **write_memory** as a new file
3. **Do NOT delete** any existing file that was not mentioned in the LLM response.

This preserves the LLM prompt's contract: "Output the COMPLETE updated tier structure" is reinterpreted as "the complete set of changes/additions", while existing untouched memories are preserved.

Key implementation detail: matching is by `title` field from the frontmatter. The `entities.parse_memory()` function returns a `MemoryFrontmatter` with a `.title` attribute.

Also update the decay step (lines 565-575) which currently only iterates `new_consolidated_paths` and `new_core_paths`. After the merge change, decay must iterate **all** files in the tier directories (not just newly written ones) to correctly apply decay to both old and new memories.

### Step 3: Add pre-consolidation snapshot

Location: `src/entity_shutdown.py`, add a helper function and call it before Step 7.

Create a function `_snapshot_tiers(entity_dir: Path)` that:

1. Creates `.entities/<name>/memories/.snapshot_pre_consolidation/` (overwriting any previous snapshot)
2. Copies `consolidated/` → `.snapshot_pre_consolidation/consolidated/`
3. Copies `core/` → `.snapshot_pre_consolidation/core/`
4. Uses `shutil.copytree` for the copy

Call this function after Step 5 (API call) but before Step 7 (merge). This means we snapshot right before any tier modifications occur.

The snapshot is intentionally a single-depth backup (not versioned). It provides one-step recovery for the most recent consolidation. Full history is available via git if the entity directory is tracked.

### Step 4: Rewrite `test_replaces_existing_tiers` to assert merge behavior

Location: `tests/test_entity_shutdown.py`, the existing `test_replaces_existing_tiers` method.

Rename to `test_merges_with_existing_tiers` and update assertions:

- Pre-existing "Old consolidated memory" and "Old core memory" should **survive** alongside the new memories from the LLM response.
- Assert total file counts = old + new (not just new).
- Assert both old and new content is present on disk.

### Step 5: Run all tests and verify green

Run `uv run pytest tests/test_entity_shutdown.py -v` and confirm:
- All 4 new tests pass
- The rewritten `test_merges_with_existing_tiers` passes
- All other existing tests still pass (no regressions)

### Step 6: Add backreference comment

Add a chunk backreference at the merge logic in `src/entity_shutdown.py`:

```python
# Chunk: docs/chunks/entity_shutdown_memory_wipe - Merge tiers instead of replace
```

## Risks and Open Questions

- **Title matching for updates**: If the LLM returns a memory with a slightly different title than the existing one (e.g., "Template system editing" vs "Template system requires source editing"), it will be treated as a new memory rather than an update. This is acceptable for this fix — the worst case is a duplicate memory, not data loss. The decay system's capacity pressure will handle duplicates over time.

- **LLM prompt says "Output the COMPLETE updated tier structure"**: The prompt (line 138) asks the LLM for a complete replacement set, but the pipeline was interpreting this too literally. The fix reinterprets the response as "changes and additions" rather than "the complete state." A future improvement could clarify the prompt to say "output ONLY changed or new memories," but that's out of scope for this bug fix.

- **Snapshot disk usage**: Each consolidation overwrites the previous snapshot. For entities with many memories, this doubles the disk usage of the memory directories. This is acceptable since memory files are small markdown files.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
