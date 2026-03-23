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

CRITICAL: Fix `ve entity shutdown` deleting existing consolidated and core memories instead of merging new journals into them.

Running shutdown with new journal memories causes ALL existing consolidated (24) and core (8) memories to be wiped. The command reports "Consolidated: 0, Core: 0" — the consolidation pipeline overwrites the memory directories instead of merging. Core memories with salience 5 and active reinforcement are destroyed on a single consolidation pass.

Root cause hypothesis: The LLM consolidation prompt returns only the newly consolidated memories (or empty set), and the pipeline interprets that as the complete replacement for the tier rather than an incremental addition. When the LLM returns nothing for consolidated/core (because 18 new journals don't warrant immediate promotion), the pipeline deletes all existing files in those directories.

Fix must ensure:
1. Existing consolidated and core memories are PRESERVED unless explicitly demoted by the decay system
2. The consolidation pipeline MERGES new promotions into existing tiers, not replaces them
3. If the LLM consolidation returns empty results, existing memories are untouched
4. A backup/snapshot mechanism before any tier modification (defense in depth)

Reported by palette/creator entity after losing 8 core memories including foundational product vision and architectural knowledge.

## Success Criteria

- Existing consolidated memories survive a shutdown with new journal entries
- Existing core memories survive a shutdown with new journal entries
- LLM consolidation returning empty results leaves existing tiers untouched
- New journal promotions are ADDED to existing tiers, not replace them
- Tests verify: run shutdown with pre-existing core/consolidated + new journals, verify all tiers preserved + new promotions added
- Recovery: if possible, provide a way to recover from accidental wipes (e.g., git-backed memory directories)

