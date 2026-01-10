<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk updates the workflow_artifacts subsystem documentation to reflect the
completed causal ordering system. The work is entirely documentation—no code changes.

The approach:
1. Revise Hard Invariant #1 to document `created_after` as the ordering mechanism
2. Add a new "Causal Ordering" subsection explaining the DAG-based ordering system
3. Verify and update the ArtifactIndex documentation in Implementation Locations
4. Add a new Known Deviation for external chunk references
5. Update the subsystem's proposed_chunks frontmatter if needed

Key references:
- Investigation 0001 (docs/investigations/0001-artifact_sequence_numbering/OVERVIEW.md)
  contains the detailed findings and design decisions
- DEC-002 (git not assumed) - explains why ArtifactIndex uses directory enumeration
  rather than git-hash-based staleness detection

No tests needed since this is documentation-only.

## Subsystem Considerations

- **docs/subsystems/0002-workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS
  documentation updates for this subsystem. The subsystem is in REFACTORING status,
  meaning we should opportunistically improve what we touch. Since this is a
  documentation-only chunk updating the subsystem's own OVERVIEW.md, all changes
  are directly in scope.

## Sequence

### Step 1: Revise Hard Invariant #1

Update Hard Invariant #1 in `docs/subsystems/0002-workflow_artifacts/OVERVIEW.md` to:
- Document `created_after` as the primary ordering mechanism
- Note that sequence prefixes (`{NNNN}-`) are legacy, being retired
- Explain that short names must be unique within artifact type (not globally)

**Current text** (lines 277-279):
> Directory naming must follow `{NNNN}-{short_name}` pattern - Sequential 4-digit
> numbering ensures chronological ordering; short_name provides human readability.
> Violation breaks enumeration, sorting, and cross-references.

**New text** should explain:
- Ordering now comes from `created_after` frontmatter field
- Sequence prefix is legacy (will be fully retired, no backwards compatibility needed)
- Terminal state: directories named `{short_name}/` only
- Short name uniqueness is per-type

### Step 2: Add new Hard Invariant for `created_after`

Add a new Hard Invariant (after updating #1) that specifies:
- Every workflow artifact must have a `created_after` field in frontmatter
- The field is an array of short names (parent artifacts)
- Empty array means the artifact is a root (no causal parents)
- Multiple entries represent merged branches (multiple tips at creation time)

This makes `created_after` a hard requirement for the workflow artifacts pattern.

### Step 2.5: Document directory naming transition

Add a section (could be a Soft Convention or separate subsection) documenting:

**Current state**:
- All existing artifacts use `{NNNN}-{short_name}/` directory naming
- New artifacts are still created with sequence prefixes
- Short names are unique within each artifact type (not globally)

**Terminal state**:
- Directory naming will be `{short_name}/` only
- Sequence prefixes will be fully retired (no backwards compatibility needed)
- All existing artifacts will be renamed as part of the migration
- See investigation 0001 proposed chunks for the migration work

**Why this matters**:
- Agents should reference artifacts by short name, not full directory name
- The sequence prefix is semantically meaningless (ordering comes from `created_after`)
- Simpler naming reduces cognitive overhead and path length

### Step 3: Add Causal Ordering section to Implementation Locations

Expand the existing "Artifact Ordering" section in Implementation Locations to include:
- Detailed explanation of causal ordering semantics
- Multi-parent DAG handling (merged branches)
- Tip identification (artifacts with no dependents)
- Topological sort algorithm (Kahn's)

Reference the investigation's findings for technical details.

### Step 4: Add Known Deviation for External Chunk References

Add a new entry to the Known Deviations section:

**External Chunk References Not in Causal Ordering**

- **Location**: `src/artifact_ordering.py`, `src/models.py#ExternalChunkRef`
- **Issue**: `ArtifactIndex` only processes directories with GOAL.md. External chunks
  have `external.yaml` instead, so they're excluded from causal ordering.
- **Impact**: High. External chunks are invisible to ordering, always appear as orphans.
  This violates the invariant that all workflow artifacts participate in causal ordering.
- **Proposed fix**: Add `created_after` to `ExternalChunkRef` model, update `ArtifactIndex`
  to read from external.yaml. See investigation 0001 proposed chunk.

### Step 5: Add chunk reference to subsystem frontmatter

Add this chunk to the subsystem's `chunks` frontmatter array:
```yaml
- chunk_id: 0043-subsystem_docs_update
  relationship: implements
```

### Step 6: Verify and update proposed_chunks

Check if the proposed chunk for external chunk causal ordering should be added
to the subsystem's `proposed_chunks` frontmatter. This would track the work needed
to fix the new deviation.

Reference: Investigation 0001 has this proposed chunk:
> "Add `created_after: list[str]` field to ExternalChunkRef model in models.py.
> Update ArtifactIndex to handle external chunk references..."

## Dependencies

- Chunks 0037-0042 (causal ordering implementation) must be complete - they are,
  as indicated by investigation 0001's proposed_chunks having chunk_directory values

## Risks and Open Questions

- **Scope of external reference deviation**: Investigation 0001 proposes adding
  `created_after` to ExternalChunkRef, but there's also a larger consolidation
  effort (ExternalArtifactRef) proposed. The deviation documentation should
  reference both possibilities without prescribing the solution.

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