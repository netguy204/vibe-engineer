---
status: ACTIVE
ticket: null
parent_chunk: artifact_ordering_index
code_paths:
- src/artifact_ordering.py
- tests/test_artifact_ordering.py
code_references:
- ref: src/artifact_ordering.py#_enumerate_artifacts
  implements: Directory enumeration for staleness detection without git
- ref: src/artifact_ordering.py#ArtifactIndex::_is_index_stale
  implements: Directory set comparison for staleness detection
- ref: src/artifact_ordering.py#ArtifactIndex::_build_index_for_type
  implements: Index building with directories list instead of hashes
- ref: tests/test_artifact_ordering.py#TestEnumerateArtifacts
  implements: Tests for directory enumeration function
- ref: tests/test_artifact_ordering.py#TestNonGitOperation
  implements: Tests verifying git-free operation
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after:
- populate_created_after
---

# Chunk Goal

## Minor Goal

`ArtifactIndex` staleness detection works without git by using directory enumeration instead of file content hashing. This aligns with DEC-002 (git not assumed) and leverages the key insight that `created_after` is immutable after artifact creation.

Because `created_after` never changes after creation, the system only needs to detect when artifacts are added or removed — not when their contents change. Two prior problems motivated this:
1. **Git dependency**: hashing depended on `git hash-object`, violating DEC-002 and failing or degrading in non-git environments
2. **Unnecessary complexity**: content hashing detected changes that, by construction, could not affect the ordering

The current approach:
- Caches the set of artifact directory names alongside the ordered list and tips
- On access, enumerates current directories and compares against the cached set
- If sets differ, rebuilds; otherwise uses cached values
- Uses no external commands (pure Python `pathlib` operations)

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

**What prompted this work**: The parent chunk's original `ArtifactIndex` implementation used git-hash-based staleness detection. While functional, that approach:
- Violated DEC-002 by depending on git
- Was more complex than necessary given `created_after` immutability

**What remains valid from parent**:
- `ArtifactIndex` class structure and public API (`get_ordered()`, `find_tips()`, `rebuild()`)
- `ArtifactType` enum
- `_topological_sort_multi_parent()` algorithm
- `_parse_created_after()` frontmatter parsing
- Index file format (JSON with ordered, tips, and per-type data)
- Gitignored index file approach (`.artifact-order.json`)

**What changed**:
- Directory set comparison replaces `_get_git_hash()` and `_get_all_artifact_hashes()`
- `_is_index_stale()` compares directory sets instead of file hashes
- The index format stores a `directories` set instead of a `hashes` field
- `_build_index_for_type()` stores the directory set instead of hashes