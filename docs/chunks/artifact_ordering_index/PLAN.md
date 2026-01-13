<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Build a cached `ArtifactIndex` class that provides ordered artifact listings and tip identification. The design follows the validated prototypes from `docs/investigations/0001-artifact_sequence_numbering/prototypes/`:

1. **Core algorithm**: Kahn's algorithm for topological sort (handles multi-parent DAGs)
2. **Staleness detection**: Git blob hashes via batched `git hash-object` (reliable across merges)
3. **Index format**: JSON with ordered lists, tips, and per-file hashes for staleness
4. **Fallback**: When `created_after` is empty, fall back to sequence number ordering

The implementation will be a standalone module `src/artifact_ordering.py` that other modules (chunks.py, narratives.py, etc.) can use. This follows the existing pattern where each domain has its own manager class.

Per docs/trunk/TESTING_PHILOSOPHY.md, we'll use TDD: write failing tests first, then implement. Tests focus on meaningful behavior (ordering correctness, staleness detection, tip identification) rather than trivial assertions.

## Subsystem Considerations

- **docs/subsystems/0002-workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS causal ordering infrastructure for the subsystem. The `ArtifactIndex` class will become a key component of workflow artifact management.

## Sequence

### Step 1: Define the ArtifactType enum and ArtifactIndex interface

Create `src/artifact_ordering.py` with:
- `ArtifactType` enum: `CHUNK`, `NARRATIVE`, `INVESTIGATION`, `SUBSYSTEM`
- `ArtifactIndex` class skeleton with public API:
  - `get_ordered(artifact_type: ArtifactType) -> list[str]`
  - `find_tips(artifact_type: ArtifactType) -> list[str]`
  - `rebuild(artifact_type: ArtifactType | None = None) -> None`

Location: `src/artifact_ordering.py`

Backreference:
```python
# Chunk: docs/chunks/0038-artifact_ordering_index - Causal ordering infrastructure
# Subsystem: docs/subsystems/0002-workflow_artifacts - Artifact ordering
```

### Step 2: Write tests for topological sort

Write tests for the topological sort algorithm before implementing it. Test cases:
- Empty graph returns empty list
- Single node with no parents
- Linear chain (A -> B -> C)
- Multi-parent DAG (A, B -> C where C depends on both)
- Disconnected components

Location: `tests/test_artifact_ordering.py`

### Step 3: Implement topological sort (Kahn's algorithm)

Implement `_topological_sort_multi_parent()` as a private function:
- Input: `dict[str, list[str]]` mapping artifact name to list of parent names
- Output: `list[str]` in causal order (oldest first)
- Use Kahn's algorithm as prototyped in `prototypes/git_hash_staleness.py`

The function handles DAGs with multiple parents per node and maintains deterministic output via sorted queue operations.

Location: `src/artifact_ordering.py`

### Step 4: Write tests for git hash staleness detection

Write tests for staleness detection before implementing. Test cases:
- Fresh index is not stale
- New artifact makes index stale
- Deleted artifact makes index stale
- Modified artifact (content change) makes index stale
- Unrelated file change does not make index stale

Use temporary git repositories for realistic testing.

Location: `tests/test_artifact_ordering.py`

### Step 5: Implement git hash utilities

Implement git hash functions:
- `_get_git_hash(file_path: Path) -> str | None`: Single file hash
- `_get_all_goal_hashes(artifact_dir: Path, artifact_type: ArtifactType) -> dict[str, str]`: Batched hash for all goal/overview files

Use batched `git hash-object` for efficiency as in the prototype.

Location: `src/artifact_ordering.py`

### Step 6: Write tests for frontmatter parsing

Write tests for extracting `created_after` from frontmatter:
- Handles empty `created_after` (returns empty list)
- Handles list of short names
- Handles legacy single string (converts to list)
- Handles missing field (defaults to empty list)
- Returns None for invalid YAML

Location: `tests/test_artifact_ordering.py`

### Step 7: Implement frontmatter parsing

Implement `_parse_artifact_frontmatter()`:
- Parse YAML frontmatter from GOAL.md (chunks) or OVERVIEW.md (others)
- Extract `created_after` field, normalizing to list
- Use existing models from `src/models.py` where appropriate

Location: `src/artifact_ordering.py`

### Step 8: Write tests for index build and query

Write tests for the full index lifecycle:
- Build index for chunks with no `created_after` (sequence number fallback)
- Build index with `created_after` populated (causal ordering)
- Find tips correctly identifies artifacts with no dependents
- Query returns cached results when index is fresh
- Query rebuilds when index is stale

Location: `tests/test_artifact_ordering.py`

### Step 9: Implement index build

Implement `_build_index()`:
1. Enumerate artifact directories
2. Get git hashes for all goal files (batched)
3. Parse frontmatter to build dependency graph
4. Topological sort with fallback to sequence order
5. Identify tips (artifacts not referenced in any `created_after`)
6. Return index dict with: `ordered`, `tips`, `hashes`, `version`

Location: `src/artifact_ordering.py`

### Step 10: Implement index storage and staleness check

Implement:
- `_load_index()`: Load JSON from `.artifact-order.json`
- `_save_index()`: Save JSON to `.artifact-order.json`
- `_is_index_stale()`: Compare current hashes to cached hashes

Index file stored in project root, not in docs directory.

Location: `src/artifact_ordering.py`

### Step 11: Implement public API methods

Wire up the public API:
- `get_ordered()`: Load/rebuild index, return ordered list
- `find_tips()`: Load/rebuild index, return tips list
- `rebuild()`: Force rebuild for specified type or all types

Handle edge cases:
- No artifacts exist (return empty lists)
- git not available (fall back to sequence order)
- Invalid frontmatter (skip artifact, warn)

Location: `src/artifact_ordering.py`

### Step 12: Add .artifact-order.json to .gitignore

Add the index file pattern to `.gitignore`:
```
.artifact-order.json
```

Per investigation findings, the index is derived data and should not be version controlled.

Location: `.gitignore`

### Step 13: Write integration tests with real artifact structure

Write tests that:
- Create a temp project with multiple chunks
- Set `created_after` in some chunks
- Verify ordering matches expected causal order
- Verify tips are correctly identified
- Verify index file is created and used

These tests validate the full flow matches the investigation's prototype behavior.

Location: `tests/test_artifact_ordering.py`

### Step 14: Performance validation

Add a test that validates performance criteria:
- Cold rebuild < 100ms for ~40 artifacts (current scale)
- Warm query < 20ms

Use `time.perf_counter()` to measure. If tests fail on slow machines, mark as approximate (not hard failures).

Location: `tests/test_artifact_ordering.py`

## Dependencies

- `ordering_field` (ACTIVE): The `created_after` field must exist in frontmatter models. ✓ Complete.
- `pyyaml`: Already a project dependency
- `pydantic`: Already a project dependency

No new dependencies required.

## Risks and Open Questions

1. **Non-git environments**: DEC-002 says git is not assumed. The implementation should fall back gracefully to sequence ordering when git is unavailable. This is explicitly handled in Step 11.

2. **Cross-type references**: `created_after` contains short names only. If a chunk references a narrative in the future, we'd need to prefix with type. Current design assumes same-type references only, which matches the investigation's design.

3. **Large repos**: Performance extrapolations suggest 1000 chunks would take ~300ms for staleness check. This is acceptable but worth monitoring.

4. **Index file location**: Storing in project root (`.artifact-order.json`) vs docs directory. Project root chosen for simplicity and to avoid polluting docs directory.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
