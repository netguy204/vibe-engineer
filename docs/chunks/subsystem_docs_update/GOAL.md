---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- docs/subsystems/0002-workflow_artifacts/OVERVIEW.md
code_references:
- ref: docs/subsystems/0002-workflow_artifacts/OVERVIEW.md
  implements: 'Documentation of causal ordering system (Hard Invariants #1-#2, Artifact
    Ordering section, Directory Naming Transition, Known Deviation for external chunks)'
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after:
- causal_ordering_migration
---

# Chunk Goal

## Minor Goal

Update the workflow_artifacts subsystem documentation to reflect the completed causal ordering system. This chunk captures the architectural evolution from sequence-number-based ordering to causal DAG ordering via `created_after` fields. Documenting this change is essential because:

1. **Invariants must match implementation** - Hard Invariant #1 currently mandates `{NNNN}-{short_name}` directory naming as the ordering mechanism. With causal ordering implemented, sequence prefixes become legacy.

2. **Agent guidance** - Agents need to understand that ordering now comes from `created_after` fields in frontmatter, not directory prefixes. This affects how they reason about artifact relationships.

3. **Future work enablement** - Documenting sequence prefixes as legacy prepares for Phase 4 chunks that will remove the prefix requirement entirely.

## Success Criteria

1. **Hard Invariant #1 updated** - Revised to describe `created_after` as the primary ordering mechanism, with sequence prefixes noted as legacy (still supported for backward compatibility)

2. **Causal ordering semantics documented** - New section or expanded content explaining:
   - `created_after` field semantics (array of parent short names)
   - Multi-parent DAG handling (merged branches create multiple parents)
   - Tip identification (artifacts with no dependents)
   - Ordering algorithm (topological sort via Kahn's algorithm)

3. **ArtifactIndex documented** - Implementation Locations section includes `ArtifactIndex` details (already partially done, verify completeness)

4. **Directory naming transition documented** - Clear statement that:
   - Current: All existing artifacts use `{NNNN}-{short_name}/`, new artifacts still created with prefix
   - Terminal: `{short_name}/` only (sequence prefixes fully retired, no backwards compatibility)
   - Short names unique within artifact type (not globally)
   - Sequence prefix is semantically meaningless (ordering comes from `created_after`)
   - Reference investigation 0001 proposed chunks for migration work

5. **New non-compliance documented in Known Deviations** - Add deviation for external chunk references not participating in causal ordering:
   - `ArtifactIndex` currently excludes directories with `external.yaml` (only processes GOAL.md)
   - `ExternalChunkRef` model lacks `created_after` field
   - Impact: External chunks are invisible to causal ordering, always appear as orphans
   - Proposed fix: See investigation 0001 proposed chunk for external chunk causal ordering