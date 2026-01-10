---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/artifact_ordering.py
  - tests/test_artifact_ordering.py
code_references:
  - ref: src/artifact_ordering.py#ArtifactType
    implements: "Enum defining workflow artifact types (CHUNK, NARRATIVE, INVESTIGATION, SUBSYSTEM)"
  - ref: src/artifact_ordering.py#ArtifactIndex
    implements: "Main class providing cached ordering and tip identification for artifacts"
  - ref: src/artifact_ordering.py#ArtifactIndex::get_ordered
    implements: "Returns topologically sorted artifact names in causal order"
  - ref: src/artifact_ordering.py#ArtifactIndex::find_tips
    implements: "Identifies artifacts with no dependents (current work frontiers)"
  - ref: src/artifact_ordering.py#ArtifactIndex::rebuild
    implements: "Forces index regeneration for specified artifact type"
  - ref: src/artifact_ordering.py#_topological_sort_multi_parent
    implements: "Kahn's algorithm for multi-parent DAG topological sorting"
  - ref: src/artifact_ordering.py#_get_git_hash
    implements: "Single file git blob hash for staleness detection"
  - ref: src/artifact_ordering.py#_get_all_artifact_hashes
    implements: "Batched git hash-object for efficient staleness checking"
  - ref: src/artifact_ordering.py#_parse_created_after
    implements: "Extracts created_after field from YAML frontmatter"
  - ref: tests/test_artifact_ordering.py
    implements: "Comprehensive test suite (43 tests) for artifact ordering"
narrative: null
subsystems:
  - subsystem_id: "0002-workflow_artifacts"
    relationship: implements
---

# Chunk Goal

## Minor Goal

Implement `ArtifactIndex` - a cached ordering system for workflow artifacts that uses git-hash-based staleness detection and topological sorting. This is the second chunk in the causal ordering initiative from `docs/investigations/0001-artifact_sequence_numbering`.

This chunk builds on `0037-created_after_field` which added the `created_after` field to all frontmatter models. The `ArtifactIndex` class will:

1. **Cache ordered artifact lists** - Avoid re-parsing all frontmatter on every list operation
2. **Detect staleness via git hashes** - Reliable across merges, checkouts, and parallel work
3. **Support multi-parent DAGs** - Handle merged branches where artifacts have multiple parents
4. **Identify tips** - Find artifacts with no dependents (current frontiers of work)

This enables subsequent chunks to:
- Populate `created_after` on artifact creation (needs `find_tips()`)
- Update list commands to use causal order (needs `get_ordered()`)

## Success Criteria

- `src/artifact_ordering.py` exists with `ArtifactIndex` class
- `ArtifactIndex.get_ordered(artifact_type)` returns topologically sorted artifact names
- `ArtifactIndex.find_tips(artifact_type)` returns artifacts with no dependents
- Git-hash-based staleness detection via batched `git hash-object`
- Index stored as gitignored JSON (`.artifact-order.json`)
- Topological sort uses Kahn's algorithm for multi-parent DAG support
- Falls back gracefully when `created_after` is empty (sequence number order)
- Cold rebuild completes in <100ms for 36 artifacts (current count)
- Warm query completes in <20ms (load + staleness check)
- All tests pass
- Prototypes in `docs/investigations/0001-artifact_sequence_numbering/prototypes/` used as reference:
  - `git_hash_staleness.py` - Git hash batching and staleness detection
  - `cached_ordering.py` - Index format and caching strategy

## Reference Implementation

See `docs/investigations/0001-artifact_sequence_numbering/prototypes/git_hash_staleness.py` for the validated prototype. Key design decisions from the investigation:

- **Index is gitignored**: Derived data, cheap to rebuild (~33ms for 36 chunks)
- **Git hashes over mtimes**: Mtimes unreliable across merges/checkouts
- **`created_after` is an array**: Merges create multiple tips; DAG not linked list
- **Batched hash-object**: Single git command for all files reduces overhead