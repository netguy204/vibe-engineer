---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
  - src/git_utils.py
  - tests/test_git_utils.py
code_references:
  - file: src/git_utils.py
    ranges:
      - lines: 11-39
        implements: "get_current_sha() function - returns HEAD SHA, validates path exists and is git repo"
      - lines: 42-75
        implements: "resolve_ref() function - resolves branch/tag/symbolic refs to SHA with error handling"
  - file: tests/test_git_utils.py
    ranges:
      - lines: 53-90
        implements: "TestGetCurrentSha - tests SHA retrieval, error cases, 40-char validation"
      - lines: 127-175
        implements: "TestResolveRef - tests branch/tag/HEAD resolution, error cases"
      - lines: 216-263
        implements: "TestWorktreeSupport - validates both functions work with git worktrees"
narrative: 0001-cross_repo_chunks
---

<!--
Do not delete this front matter description text until the chunk complete
command is run. This describes schema information that needs to be adhered
to throughout the process. 

STATUS VALUES:
- IMPLEMENTING: This chunk is in the process of being implemented. 
- ACTIVE: This chunk accurately describes current or recently-merged work
- SUPERSEDED: Another chunk has modified the code this chunk governed
- HISTORICAL: Significant drift; kept for archaeology only

PARENT_CHUNK:
- null for new work
- chunk directory name (e.g., "006-segment-compaction") for corrections or modifications

CODE_PATHS:
- Populated at planning time
- List files you expect to create or modify
- Example: ["src/segment/writer.rs", "src/segment/format.rs"]

CODE_REFERENCES:
- Populated after implementation, before PR
- Maps specific line ranges to what they implement
- Example:
  code_references:
    - file: src/segment/writer.rs
      ranges:
        - lines: 45-120
          implements: "SegmentWriter struct and core write loop"
        - lines: 122-145
          implements: "fsync durability guarantees"

NARRATIVE:
- If this chunk was derived from a narrative document, reference the narrative directory name. 
-->

# Chunk Goal

## Minor Goal

Create utility functions for working with local git repositories and worktrees. This directly supports the trunk GOAL.md's required property: "It must be possible to perform the workflow outside the context of a Git repository."

When working in a task directory that contains multiple git worktrees, the `ve sync` command needs to resolve SHAs and update `pinned` fields in `external.yaml` files. This chunk provides the foundational git operations that make that possible:

1. **`get_current_sha(repo_path) -> str`** - Get the HEAD SHA of a local repository
2. **`resolve_ref(repo_path, ref) -> str`** - Resolve a branch, tag, or ref to its SHA

These utilities operate entirely on local worktrees within the task directory, avoiding network operations. They form the foundation for:
- The `ve sync` command (chunk 6) which updates `pinned` fields
- The `ve external resolve` command (chunk 7) which displays external chunk content

## Success Criteria

1. **`get_current_sha(repo_path) -> str`** is implemented:
   - Returns the full 40-character SHA of HEAD
   - Raises `ValueError` if path is not a git repository
   - Works with both regular repositories and worktrees

2. **`resolve_ref(repo_path, ref) -> str`** is implemented:
   - Returns the full 40-character SHA that the ref points to
   - Handles branch names (e.g., `main`, `feature/foo`)
   - Handles tag names (e.g., `v1.0.0`)
   - Handles symbolic refs (e.g., `HEAD`, `HEAD~1`)
   - Raises `ValueError` if path is not a git repository
   - Raises `ValueError` if ref does not exist

3. **Error handling** is robust:
   - Clear error messages that include the path and ref in question
   - Appropriate exception types for different failure modes

4. **Unit tests** validate:
   - Successful SHA retrieval from a git repository
   - Successful ref resolution for branches and tags
   - Error cases: non-existent path, non-git directory, invalid ref
   - Both functions work correctly with git worktrees