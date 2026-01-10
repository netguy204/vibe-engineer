---
status: SOLVED
trigger: Parallel work (teams, worktrees) creates conflicting sequence numbers
proposed_chunks:
- prompt: 'Add `created_after: list[str]` field to ChunkFrontmatter, NarrativeFrontmatter,
    InvestigationFrontmatter, and SubsystemFrontmatter Pydantic models in models.py.
    Field is optional (defaults to empty list) for backward compatibility. This is
    an array of short names referencing parent artifacts for causal ordering.'
  chunk_directory: created_after_field
- prompt: Create src/artifact_ordering.py with ArtifactIndex class for caching ordered
    artifact lists. Include git-hash-based staleness detection, topological sort for
    multi-parent DAGs (Kahn's algorithm), find_tips() to identify artifacts with no
    dependents. Index stored as gitignored JSON. See investigation prototypes for
    reference implementation.
  chunk_directory: artifact_ordering_index
- prompt: Update create_chunk(), create_narrative(), create_investigation(), create_subsystem()
    to find current tips using ArtifactIndex and set created_after to list of tip
    short names. Pass to template for frontmatter generation.
  chunk_directory: populate_created_after
- prompt: Modify ve chunk list, ve narrative list, ve investigation list, ve subsystem
    list to use ArtifactIndex for ordering instead of sequence number parsing. Fall
    back to sequence order when created_after not populated. Display tip indicators
    for artifacts with no dependents.
  chunk_directory: artifact_list_ordering
- prompt: Create ve migrate causal-ordering command that migrates ALL artifact types
    (chunks, narratives, investigations, subsystems). For each type, sort existing
    artifacts by sequence number and set each artifact's created_after to [previous
    artifact's short name]. First artifact of each type gets empty created_after.
    Short names only need to be unique within their artifact type. See investigation
    prototypes for migration strategy.
  chunk_directory: causal_ordering_migration
- prompt: 'Update docs/subsystems/0002-workflow_artifacts/OVERVIEW.md to revise Hard
    Invariant #1 for new naming pattern, document created_after field and causal ordering
    semantics, add ArtifactIndex to Implementation Locations, note sequence prefixes
    as legacy.'
  chunk_directory: subsystem_docs_update
- prompt: Update artifact creation for ALL types (chunks, narratives, investigations,
    subsystems) to use short_name/ instead of NNNN-short_name/ for directory naming.
    Add collision detection within each artifact type (short names only need to be
    unique within their type). Update all code that parses directory names. Support
    both patterns during transition.
  chunk_directory: remove_sequence_prefix
- prompt: 'Update all cross-references across ALL artifact types from NNNN-short_name
    to short_name format: code backreferences (# Chunk:, # Subsystem:), frontmatter
    references (narrative, subsystems.chunk_id, parent_chunk, chunks in subsystem
    frontmatter), subsystem code_references. Create automated migration tool for existing
    cross-refs. References remain type-qualified (e.g., docs/chunks/foo, docs/narratives/bar)
    so cross-type name collisions are not an issue.'
  chunk_directory: update_crossref_format
- prompt: 'Add `created_after: list[str]` field to ExternalChunkRef model in models.py.
    Update ArtifactIndex to handle external chunk references: enumerate directories
    with external.yaml when GOAL.md doesn''t exist, read created_after from external.yaml
    (plain YAML, not markdown frontmatter), hash external.yaml for staleness detection.
    Update chunk creation flow (task_utils.py) to set created_after when creating
    external.yaml references. This ensures external chunks participate in local causal
    ordering.'
  chunk_directory: null
created_after: []
---

<!--
DO NOT DELETE THIS COMMENT until the investigation reaches a terminal status.
This documents the frontmatter schema and guides investigation workflow.

STATUS VALUES:
- ONGOING: Investigation is active; exploration and analysis in progress
- SOLVED: The question has been answered or the problem has been resolved
- NOTED: Findings documented but no action required; kept for future reference
- DEFERRED: Investigation paused; may be revisited later when conditions change

TRIGGER:
- Brief description of what prompted this investigation
- Examples:
  - "Test failures in CI after dependency upgrade"
  - "User reported slow response times on dashboard"
  - "Exploring whether GraphQL would simplify our API"
- The trigger naturally captures whether this is an issue (problem to solve)
  or a concept (opportunity to explore)

PROPOSED_CHUNKS:
- Starts empty; entries are added if investigation reveals actionable work
- Each entry records a chunk prompt for work that should be done
- Format: list of {prompt, chunk_directory} where:
  - prompt: The proposed chunk prompt text
  - chunk_directory: Populated when/if the chunk is actually created via /chunk-create
- Unlike narrative chunks (which are planned upfront), these emerge from investigation findings
-->

## Trigger

Parallel work scenarios create conflicting sequence numbers in artifact storage:

- **Teams in separate clones**: Multiple developers creating artifacts simultaneously generate the same sequence number (e.g., two people both create chunk `0037-...`)
- **Conductor with multiple worktrees**: Tools encouraging parallel work across worktrees hit the same collision problem

Observation: Sequence numbers currently serve two purposes:
1. Short handle for referencing artifacts
2. Mechanism to ensure causal relationships between artifacts are maintained

Both functions might be achievable through alternative mechanisms that don't require global coordination.

## Success Criteria

1. **Merge-friendly causal relationships**: Design a mechanism for maintaining causal relationships between artifacts that doesn't conflict when parallel work is merged
2. **Performance validated**: A causally-ordered listing of chunks (the most numerous artifact type) is human-interaction fast (sub-second response)

## Testable Hypotheses

### H1: Short names alone can serve as unique artifact handles

- **Rationale**: Sequence numbers are mainly used for ordering, not uniqueness
- **Test**: Audit existing artifacts to confirm short names are unique within each artifact type; identify naming collision risks
- **Status**: VERIFIED - All 36 chunks, 3 narratives, 2 subsystems have unique short names. No cross-type collisions. See `prototypes/audit_short_names.py`.

### H2: `created_after` frontmatter can capture causal relationships

- **Rationale**: Each artifact can reference the artifact that was "current" when it was created; `parent` is already used for superseding relationships
- **Test**: Prototype the field and verify it captures the ordering we need for merge scenarios
- **Status**: VERIFIED - Array-based `created_after` handles both linear chains and multi-parent DAGs from merges. See `prototypes/creation_flow.py`.

### H3: Frontmatter-based graph traversal scales poorly

- **Rationale**: Finding causal order requires loading frontmatter from every artifact file; this is O(n) file reads
- **Test**: Measure time to produce ordered list with 100, 500, 1000 chunks
- **Status**: PARTIALLY VERIFIED - scales at ~0.9ms/chunk with real data, meaning 1000 chunks ≈ 900ms. Borderline acceptable but close to the 1-second threshold.

### H4: Finding graph tips requires reading every artifact

- **Rationale**: Without an index, there's no way to know which artifacts have no dependents without scanning all files
- **Test**: Confirm this is true; explore whether a lightweight index could mitigate
- **Status**: VERIFIED - confirmed true by construction. Tips can only be identified by checking all artifacts for references.

### H5: A cached/indexed representation can restore interactive performance

- **Rationale**: If raw traversal is too slow, a regenerable index (like a `.artifact-order` file) could cache the sorted order
- **Test**: Prototype an index approach; measure rebuild time and query time
- **Status**: VERIFIED - cached approach is 75x faster. Warm query ~0.43ms vs cold rebuild ~33ms. Extrapolated: 1000 chunks ≈ 11ms with cache.

### H6: External chunk references need `created_after` in the reference, not the chunk

- **Rationale**: An external chunk's `created_after` in its GOAL.md frontmatter tracks its position in the *external repo's* causal chain. But when referenced locally via `external.yaml`, we need to track where it fits in the *local* causal ordering. The same external chunk could be referenced from multiple projects at different points in their respective causal chains.
- **Test**: Design where `created_after` should live for external references; verify it correctly captures local causal position
- **Status**: VERIFIED - External chunks are completely excluded from ArtifactIndex. Adding `created_after` to ExternalChunkRef and updating ArtifactIndex to handle external.yaml is required.

## Exploration Log

### 2026-01-10: External chunk references and causal ordering

**Problem statement:**

External chunks create a two-chain scenario:
- The external repo has its own causal chain (chunk's GOAL.md `created_after` tracks position there)
- The local repo has its own causal chain (where does this external reference fit locally?)

Example scenario:
```
project-a/docs/chunks/
  0001-local_chunk/GOAL.md          # created_after: []
  0002-another_local/GOAL.md        # created_after: [local_chunk]
  0003-external_work/external.yaml  # Points to project-b chunk
```

Where does `0003-external_work` fit in project-a's causal chain? Its `created_after` should capture that it was added after `another_local`, regardless of where the chunk sits in project-b's causal chain.

**Design options:**

1. **Add `created_after` to ExternalChunkRef model**: The external.yaml stores the local causal position
2. **Use a companion file**: external.yaml + metadata.yaml with frontmatter
3. **External refs don't participate**: They're always tips in local ordering

**Analysis:**

Option 1 is cleanest - ExternalChunkRef already holds reference metadata (track, pinned). Adding `created_after` keeps all reference-specific data together. The same external chunk referenced from two different projects would have different `created_after` values in each project's external.yaml.

Option 2 adds file complexity for little benefit.

Option 3 breaks the causal model - external work IS causally ordered relative to local work.

**Current ExternalChunkRef structure** (from `src/models.py:215-226`):
```python
class ExternalChunkRef(BaseModel):
    repo: str  # GitHub-style org/repo format
    chunk: str  # Chunk directory name
    track: str | None = None  # Branch to follow
    pinned: str | None = None  # 40-char SHA
```

**Proposed addition:**
```python
created_after: list[str] = []  # Local causal ordering (short names)
```

**Impact on ArtifactIndex:**

The `ArtifactIndex` currently reads `created_after` from GOAL.md frontmatter. For external chunks, it needs to:
1. Detect external reference (external.yaml exists instead of GOAL.md)
2. Read `created_after` from external.yaml instead

This is a small change to the index loading logic.

**Open questions:**
- Should `ve sync` update `created_after` when syncing external refs?
- How does this interact with the planned `ExternalArtifactRef` consolidation?

**ArtifactIndex analysis:**

Reviewed `src/artifact_ordering.py`. Current implementation has a critical gap:

1. **Lines 276-280**: `_is_index_stale()` only considers directories with the main file (GOAL.md for chunks)
2. **Lines 313-318**: `_build_index_for_type()` same pattern - only includes dirs with GOAL.md
3. **`_parse_created_after()`**: Reads markdown frontmatter, not YAML files

External chunk directories have `external.yaml` instead of `GOAL.md`, so they're **completely excluded** from:
- The ordered list
- Tip identification
- Staleness detection

This confirms H6 - external chunks need special handling.

**Required changes to ArtifactIndex:**

1. When enumerating artifacts, also include directories with `external.yaml` (when GOAL.md doesn't exist)
2. For external chunks, read `created_after` from external.yaml (plain YAML, not markdown frontmatter)
3. Hash external.yaml for staleness detection (not GOAL.md)

**Code sketch:**
```python
# In _build_index_for_type and _is_index_stale:
for item in artifact_dir.iterdir():
    if item.is_dir():
        main_path = item / main_file
        external_path = item / "external.yaml"
        if main_path.exists():
            # Local artifact
            ...
        elif external_path.exists():
            # External reference
            ...
```

### 2026-01-10: Performance baseline and scaling analysis

**Baseline measurements:**
- Current artifact counts: 36 chunks, 3 narratives, 2 subsystems, 1 investigation
- Current `ve chunk list` time: ~0.26s for 36 chunks
- Current approach: ordering derived from directory name prefix (0001-, 0002-, etc.) - no file reads needed

**Frontmatter-based approach analysis:**

Reviewed `src/chunks.py:69-84` - `list_chunks()` currently just scans directories and parses numeric prefix. Fast because no file I/O for ordering.

Prototyped frontmatter-based ordering (see `prototypes/frontmatter_ordering.py`):
- Enumerate dirs: 0.35ms
- Load all frontmatter: 32.48ms (~0.9ms per chunk with real data)
- Topological sort: 0.01ms (trivial)
- **Total: ~33ms for 36 chunks**

Simulated scaling (see `prototypes/scaling_test.py`):
- 100 chunks: ~91ms (extrapolated from real data)
- 500 chunks: ~452ms
- 1000 chunks: ~903ms

Key insight: Real GOAL.md files are 80-130 lines with complex YAML (nested structures, lists), explaining ~7x slower parsing than minimal test files.

**Cached/indexed approach analysis:**

Prototyped caching (see `prototypes/cached_ordering.py`):
- Cold rebuild: ~33ms (same as above)
- Warm query (load index + staleness check): ~0.43ms
- **Speedup: 75x**

Extrapolated warm queries:
- 100 chunks: ~1.1ms
- 500 chunks: ~5.4ms
- 1000 chunks: ~10.8ms

Index format: JSON with ordered list, tips, and per-chunk mtimes for staleness detection.

**Open questions:**
- How should the index be invalidated/rebuilt? (mtime-based works but adds per-file stat calls)
- Should the index be git-tracked or gitignored?
- How to handle merge conflicts in the index file?

### 2026-01-10: Git hash staleness and multi-parent design

**Design decisions confirmed:**
- Index will be gitignored (derived, cheap to rebuild)
- Use git hashes for staleness (reliable across merges)
- `created_after` is an array (merges create multiple tips)

**Git hash performance (see `prototypes/git_hash_staleness.py`):**
- Cold rebuild: ~48ms (adds ~15ms for git hash-object vs mtime approach)
- Warm query: ~10.7ms (vs ~0.4ms with mtimes)
- Slower but acceptable: 1000 chunks would be ~300ms staleness check

The git hash-object command is batched (all files in one call), so the overhead scales sublinearly.

**Multi-parent topological sort:**
Updated prototype to handle `created_after` as an array. Uses Kahn's algorithm which naturally handles DAGs with multiple parents. A chunk appears in output only after ALL its parents.

**Tips with multi-parent:**
All current chunks show as tips because `created_after` doesn't exist yet. After migration, tips = chunks that no other chunk references in their `created_after`.

### 2026-01-10: Short name uniqueness and migration strategy

**Short name audit (see `prototypes/audit_short_names.py`):**
- All 36 chunks have unique short names
- All 3 narratives have unique short names
- All 2 subsystems have unique short names
- No cross-artifact-type collisions
- Collision prevention: descriptive names are naturally unique; can add suffixes if needed

**Creation flow (see `prototypes/creation_flow.py`):**
- New chunks set `created_after` to current tips
- After creation, new chunk becomes the (only) tip
- Collision detection prevents duplicate short names

**Migration strategy (see `prototypes/migration_strategy.py`):**
- Use sequence order to create linear chain
- Each chunk's `created_after` = [previous chunk's short name]
- First chunk has `created_after: []`
- Result: single tip (most recent chunk), chain length = 36

**Migration impact:**
- 14 cross-references in frontmatter need updating
- Code backreferences (# Chunk: docs/chunks/0001-...) need updating
- src/chunks.py regex patterns need updating
- Tests need updating

**Key insight:** Post-migration, new chunk creation is clean:
```yaml
created_after: ['chunk_frontmatter_model']  # Just the current tip
```

Instead of listing all 36 predecessors.

## Findings

### Verified Findings

1. **Frontmatter-based ordering is feasible at scale**: Even without caching, 1000 chunks can be ordered in ~900ms, meeting the sub-second threshold. With caching, this drops to ~11ms.

2. **Current ordering relies on directory names**: `list_chunks()` in `src/chunks.py` extracts numeric prefixes from directory names. This is what creates the conflict in parallel work scenarios.

3. **Caching provides 75x speedup**: A JSON index file with pre-computed order, tips, and mtimes for staleness detection reduces query time from ~33ms to ~0.43ms for 36 chunks.

4. **Topological sort is not the bottleneck**: The sort itself takes ~0.01ms. All the cost is in loading frontmatter from disk.

5. **Git hash staleness is reliable and acceptably fast**: ~10.7ms for 36 chunks (~300ms extrapolated for 1000). Batching git hash-object into a single call keeps overhead manageable.

6. **Multi-parent DAG works with standard algorithms**: Kahn's algorithm handles `created_after` arrays correctly. A chunk appears after all its parents in the sorted output.

7. **Short names are currently unique within type**: Audit confirms all artifacts have unique short names within their type. Cross-type collisions are allowed (a chunk and narrative can share a short name since references are type-qualified, e.g., `docs/chunks/foo` vs `docs/narratives/foo`).

8. **Linear migration preserves order**: Existing sequence numbers can bootstrap the `created_after` chain, resulting in a single tip after migration.

9. **External chunk references need `created_after` in the reference**: An external chunk's GOAL.md `created_after` tracks its position in the external repo's causal chain, not the local repo's. The `ExternalChunkRef` model (in external.yaml) must have its own `created_after` field to capture local causal position. The same external chunk can be referenced from multiple projects at different points in their respective causal chains.

10. **ArtifactIndex currently excludes external chunks**: The current implementation only considers directories with GOAL.md (lines 276-280, 313-318 of `src/artifact_ordering.py`). External chunk directories have external.yaml instead, so they're completely invisible to causal ordering. This must be fixed for external chunks to participate in the local causal DAG.

### Design Decisions

1. **Index will be gitignored**: It's derived data, rebuild is cheap (~33ms for 36 chunks, ~1s for 1000), and git-tracking would cause merge conflicts.

2. **Use git hashes for staleness detection**: Mtimes are unreliable across merges, checkouts, and rsync. Git blob hashes are the source of truth for content identity.

3. **`created_after` is an array**: A merge can create multiple tips. Work created after a merge is causally after ALL merged tips. This makes the causal graph a true DAG with multiple parents, not a linked list.

4. **Short name uniqueness is per-type**: Short names only need to be unique within their artifact type (chunks, narratives, investigations, subsystems). Cross-type collisions are fine because all references include the type path (e.g., `docs/chunks/foo` vs `docs/narratives/foo`). Each artifact type maintains its own independent causal ordering graph.

5. **External references store `created_after` in external.yaml**: The `ExternalChunkRef` model gets a `created_after` field to track local causal position. This is stored in external.yaml alongside repo, chunk, track, and pinned fields. The `ArtifactIndex` reads this field when processing external chunk directories.

### Hypotheses/Opinions

1. **Topological sort still works with multi-parent DAG**: Standard algorithms handle this. A chunk appears in output only after all its parents.

2. **Multiple tips are semantically correct**: Parallel work IS concurrent - there's no total order. The tips represent "current frontiers" of work.

## Proposed Chunks

### Phase 1: Foundation

1. **Add `created_after` to all frontmatter schemas**: Add `created_after: list[str]` field
   to `ChunkFrontmatter`, `NarrativeFrontmatter`, `InvestigationFrontmatter`, and
   `SubsystemFrontmatter` Pydantic models in `models.py`. Field is optional (defaults to
   empty list) for backward compatibility. This is an array of short names (not full
   directory names) referencing parent artifacts.
   - Priority: High
   - Dependencies: 0036-chunk_frontmatter_model (adds ChunkFrontmatter)
   - Subsystem: workflow_artifacts (implements)

2. **Implement causal ordering index**: Create `src/artifact_ordering.py` with:
   - `ArtifactIndex` class for caching ordered artifact lists
   - Git-hash-based staleness detection via batched `git hash-object`
   - Topological sort supporting multi-parent DAGs (Kahn's algorithm)
   - `find_tips()` to identify artifacts with no dependents
   - Index stored as gitignored JSON (e.g., `.artifact-order.json`)
   - See `prototypes/git_hash_staleness.py` for reference implementation
   - Priority: High
   - Dependencies: Chunk 1 (created_after field must exist)
   - Subsystem: workflow_artifacts (implements)

### Phase 2: Creation Flow

3. **Populate `created_after` on artifact creation**: Update `create_chunk()`,
   `create_narrative()`, `create_investigation()`, `create_subsystem()` to:
   - Find current tips using `ArtifactIndex`
   - Set `created_after` to list of tip short names
   - Pass to template for frontmatter generation
   - Priority: High
   - Dependencies: Chunks 1, 2
   - Subsystem: workflow_artifacts (implements)

4. **Update listing commands to use causal order**: Modify `ve chunk list`,
   `ve narrative list`, `ve investigation list`, `ve subsystem list` to:
   - Use `ArtifactIndex` for ordering (instead of sequence number parsing)
   - Fall back to sequence order when `created_after` not populated
   - Display tip indicators for artifacts with no dependents
   - Priority: High
   - Dependencies: Chunks 1, 2
   - Subsystem: workflow_artifacts (implements)

### Phase 3: Migration

5. **Migrate existing artifacts to use `created_after`**: Create migration script/command
   (`ve migrate causal-ordering`) that:
   - Sorts existing artifacts by sequence number
   - Sets each artifact's `created_after` to [previous artifact's short name]
   - First artifact gets empty `created_after: []`
   - Preserves existing frontmatter, only adds/updates `created_after`
   - See `prototypes/migration_strategy.py` for approach
   - Priority: High
   - Dependencies: Chunks 1-4
   - Subsystem: workflow_artifacts (implements)

6. **Update workflow_artifacts subsystem documentation**: Revise
   `docs/subsystems/0002-workflow_artifacts/OVERVIEW.md` to:
   - Update Hard Invariant #1 to describe new naming pattern (short_name only)
   - Document `created_after` field and causal ordering semantics
   - Add `ArtifactIndex` to Implementation Locations
   - Note that sequence prefixes are legacy, supported for backward compatibility
   - Priority: Medium
   - Dependencies: Chunks 1-5
   - Subsystem: workflow_artifacts (implements)

### Phase 4: Directory Naming (Future)

7. **Remove sequence prefix from directory names**: Update artifact creation to use
   `{short_name}/` instead of `{NNNN}-{short_name}/`. Update:
   - `Chunks.create_chunk()`, etc. to use short_name directly
   - Collision detection (error if short_name already exists)
   - All code that parses directory names (remove regex for `^\d{4}-`)
   - Priority: Medium
   - Dependencies: Chunks 1-6 (all existing artifacts migrated first)
   - Subsystem: workflow_artifacts (implements)
   - Notes: This is a breaking change; may want to support both patterns during transition

8. **Update cross-references to use short names**: Update all references from
   `{NNNN}-{short_name}` to `{short_name}`:
   - Code backreferences (`# Chunk: docs/chunks/...`)
   - Frontmatter references (narrative, subsystems.chunk_id, parent_chunk)
   - Subsystem code_references
   - Priority: Medium
   - Dependencies: Chunk 7
   - Subsystem: workflow_artifacts (implements)
   - Notes: May need automated migration tool; 14 cross-refs in current frontmatter

## Resolution Rationale

**Problem solved**: Designed a merge-friendly causal ordering system that eliminates
sequence number conflicts in parallel work scenarios, including proper handling of
external chunk references.

**Solution summary**:
- Replace sequence-based ordering with `created_after` frontmatter field (array of parent short names)
- Use short names as artifact handles (directories become `short_name/` instead of `NNNN-short_name/`)
- Cache ordering in gitignored JSON index with git-hash-based staleness detection
- Topological sort handles multi-parent DAGs from merged branches
- External chunk references store `created_after` in ExternalChunkRef/external.yaml to track local causal position (separate from the chunk's position in the external repo)

**Performance validated**:
- Without cache: ~900ms for 1000 chunks (acceptable)
- With cache: ~11ms for 1000 chunks (excellent)
- Git hash staleness: ~300ms for 1000 chunks (acceptable for correctness guarantee)

**Migration path**: Phased approach allows incremental adoption while maintaining
backward compatibility. 9 proposed chunks cover foundation, creation flow, migration,
directory naming, and external reference handling.

**Prototypes preserved**: All exploration code saved in `prototypes/` subdirectory
for implementation reference.