---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/entity_shutdown.py
- tests/test_entity_shutdown.py
code_references:
- ref: src/entity_shutdown.py#_snapshot_tiers
  implements: "Pre-consolidation snapshot of consolidated and core tiers for defense-in-depth recovery"
- ref: src/entity_shutdown.py#run_consolidation
  implements: "Merge-based tier update logic that preserves existing memories and adds/updates from LLM response"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- cli_dotenv_loading
---

# Chunk Goal

## Minor Goal

`ve entity shutdown` merges newly consolidated memories into the existing consolidated and core tiers rather than replacing them. Existing memories survive a shutdown that produces no new promotions for their tier.

The consolidation pipeline in `run_consolidation`:

1. Loads all existing consolidated and core memories from disk before calling the LLM, so they are visible to the consolidation prompt.
2. Snapshots the consolidated and core directories to `.snapshot_pre_consolidation/` before any modifications, providing single-step recovery if a consolidation pass goes wrong (defense in depth).
3. For each entry the LLM returns in a tier, looks up an existing file with the same title and overwrites it; entries without a title match are appended. Existing files whose titles are not present in the LLM response are left untouched — an empty LLM result for a tier therefore preserves every existing memory in that tier.

Demotion of consolidated or core memories is the responsibility of the decay system, never a side effect of consolidation.

## Success Criteria

- Existing consolidated memories survive a shutdown with new journal entries
- Existing core memories survive a shutdown with new journal entries
- LLM consolidation returning empty results leaves existing tiers untouched
- New journal promotions are ADDED to existing tiers, not replace them
- Tests verify: run shutdown with pre-existing core/consolidated + new journals, verify all tiers preserved + new promotions added
- Recovery: if possible, provide a way to recover from accidental wipes (e.g., git-backed memory directories)

