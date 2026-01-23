---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/artifact_ordering.py
- tests/test_artifact_ordering.py
code_references:
- ref: src/artifact_ordering.py#_parse_frontmatter
  implements: "Shared frontmatter parsing helper for status and created_after extraction"
- ref: src/artifact_ordering.py#_parse_status
  implements: "Status field extraction from artifact frontmatter"
- ref: src/artifact_ordering.py#_TIP_ELIGIBLE_STATUSES
  implements: "Mapping of artifact types to their tip-eligible status values"
- ref: src/artifact_ordering.py#ArtifactIndex::_build_index_for_type
  implements: "Status-aware tip filtering in index building"
- ref: tests/test_artifact_ordering.py#TestStatusFilteredTips
  implements: "Test coverage for status-filtered tip detection"
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["glob_code_paths"]
---

# Chunk Goal

## Minor Goal

Update the `find_tips` logic in `ArtifactIndex` to only consider artifacts with
ACTIVE or IMPLEMENTING (for chunks) status—or equivalent "in-progress" statuses
for other artifact types—when computing tips for `created_after` population.

### Problem

Currently, `find_tips()` returns all artifacts that are not referenced by any
other artifact's `created_after` field. This creates an issue when creating
multiple FUTURE chunks during in-progress work:

1. Operator is working on chunk A (IMPLEMENTING)
2. Operator creates FUTURE chunk B → its `created_after` is set to chunk A (the tip)
3. Operator creates FUTURE chunk C → its `created_after` is set to chunk B (now
   the tip, since B was just created and nothing references it yet)

This creates an **implied sequence** between B and C that doesn't reflect actual
causality. B and C are both conceptually "after A" since that's when they were
conceived—they shouldn't form a causal chain with each other.

### Solution

Change tip detection to filter by status for artifact types that have a
"future/queued" concept:

- **Chunks**: Only ACTIVE or IMPLEMENTING chunks are considered tips (excludes
  FUTURE, SUPERSEDED, HISTORICAL)
- **Narratives**: Only ACTIVE narratives are considered tips (excludes DRAFTING,
  COMPLETED)
- **Investigations**: No filtering (no "future" concept—ONGOING is the only
  active state, and all other states are terminal)
- **Subsystems**: No filtering (no "future" concept—all non-deprecated states
  represent active documentation)

This way:
1. Chunk A (IMPLEMENTING) is the tip
2. FUTURE chunk B → `created_after: [A]`
3. FUTURE chunk C → `created_after: [A]` (not B, because B is FUTURE and excluded)

When the operator finishes A, activates B, and starts working on it, B naturally
becomes a tip and new work will reference it appropriately.

### Why This Is Right

The `created_after` field captures **causal ordering**—what work was actually
done or in-progress when this artifact was created. FUTURE artifacts represent
*planned* work that hasn't started yet. They don't represent work that has
happened, so they shouldn't participate in the causal graph as priors.

Investigations and subsystems don't have a "future/queued" workflow—they are
either being actively explored or are in a terminal state. Filtering doesn't
apply to them.

## Success Criteria

- `ArtifactIndex.find_tips()` for chunks returns only ACTIVE or IMPLEMENTING chunks
- `ArtifactIndex.find_tips()` for narratives returns only ACTIVE narratives
- `ArtifactIndex.find_tips()` for investigations and subsystems remains unchanged
- Creating multiple FUTURE chunks in sequence all get the same `created_after`
  value (the current ACTIVE/IMPLEMENTING tip)
- Tests verify the new filtering behavior for chunks and narratives