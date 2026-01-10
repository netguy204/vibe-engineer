---
status: ACTIVE
ticket: null
parent_chunk: 0038-artifact_ordering_index
code_paths:
  - src/artifact_ordering.py
  - tests/test_artifact_ordering.py
code_references:
  - ref: src/artifact_ordering.py#_enumerate_artifacts
    implements: "Directory enumeration for staleness detection without git"
  - ref: src/artifact_ordering.py#ArtifactIndex::_is_index_stale
    implements: "Directory set comparison for staleness detection"
  - ref: src/artifact_ordering.py#ArtifactIndex::_build_index_for_type
    implements: "Index building with directories list instead of hashes"
  - ref: tests/test_artifact_ordering.py#TestEnumerateArtifacts
    implements: "Tests for directory enumeration function"
  - ref: tests/test_artifact_ordering.py#TestNonGitOperation
    implements: "Tests verifying git-free operation"
narrative: null
subsystems:
- subsystem_id: 0002-workflow_artifacts
  relationship: implements
created_after: ["0039-populate_created_after"]
---

# Chunk Goal

## Minor Goal

Simplify `ArtifactIndex` staleness detection to work without git by using directory enumeration instead of file content hashing. This aligns with DEC-002 (git not assumed) and leverages the key insight that `created_after` is immutable after artifact creation.

Currently, `ArtifactIndex` uses `git hash-object` to detect when cached ordering becomes stale. This has two problems:
1. **Git dependency**: Violates DEC-002; fails or degrades in non-git environments
2. **Unnecessary complexity**: Since `created_after` never changes after creation, we only need to detect when artifacts are added or removed—not when their contents change

The simplified approach:
- Cache the set of artifact directory names alongside the ordered list and tips
- On access, enumerate current directories and compare against cached set
- If sets differ, rebuild; otherwise use cached values
- No external commands needed (pure Python `pathlib` operations)

## Success Criteria

- `ArtifactIndex` works correctly in directories that are not git repositories
- Staleness detection uses directory enumeration, not file hashing
- `_get_git_hash()` and `_get_all_artifact_hashes()` functions are removed
- No subprocess calls to git in `artifact_ordering.py`
- Performance: directory enumeration should be faster than git hash-object calls
- All existing `ArtifactIndex` tests pass
- New tests verify correct behavior in non-git directories
- Index correctly detects:
  - New artifact directories (rebuild needed)
  - Deleted artifact directories (rebuild needed)
  - No changes (use cached values)

## Relationship to Parent

**Parent chunk**: `0038-artifact_ordering_index`

**What prompted this work**: The parent chunk implemented `ArtifactIndex` with git-hash-based staleness detection. While functional, this approach:
- Violates DEC-002 by depending on git
- Is more complex than necessary given `created_after` immutability

**What remains valid from parent**:
- `ArtifactIndex` class structure and public API (`get_ordered()`, `find_tips()`, `rebuild()`)
- `ArtifactType` enum
- `_topological_sort_multi_parent()` algorithm
- `_parse_created_after()` frontmatter parsing
- Index file format (JSON with ordered, tips, and per-type data)
- Gitignored index file approach (`.artifact-order.json`)

**What is being changed**:
- Replace `_get_git_hash()` and `_get_all_artifact_hashes()` with directory set comparison
- Modify `_is_index_stale()` to compare directory sets instead of file hashes
- Remove `hashes` field from index format (replaced with `directories` set)
- Update `_build_index_for_type()` to store directory set instead of hashes