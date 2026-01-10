---
status: FUTURE
ticket: null
parent_chunk: 0038-artifact_ordering_index
code_paths: []
code_references: []
narrative: null
subsystems:
  - subsystem_id: "0002-workflow_artifacts"
    relationship: implements
---

<!--
╔══════════════════════════════════════════════════════════════════════════════╗
║  DO NOT DELETE THIS COMMENT BLOCK until the chunk complete command is run.   ║
║                                                                              ║
║  AGENT INSTRUCTIONS: When editing this file, preserve this entire comment    ║
║  block. Only modify the frontmatter YAML and the content sections below      ║
║  (Minor Goal, Success Criteria, Relationship to Parent). Use targeted edits  ║
║  that replace specific sections rather than rewriting the entire file.       ║
╚══════════════════════════════════════════════════════════════════════════════╝

This comment describes schema information that needs to be adhered
to throughout the process.

STATUS VALUES:
- FUTURE: This chunk is queued for future work and not yet being implemented
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
- Uses symbolic references to identify code locations
- Format: {file_path}#{symbol_path} where symbol_path uses :: as nesting separator
- Example:
  code_references:
    - ref: src/segment/writer.rs#SegmentWriter
      implements: "Core write loop and buffer management"
    - ref: src/segment/writer.rs#SegmentWriter::fsync
      implements: "Durability guarantees"
    - ref: src/utils.py#validate_input
      implements: "Input validation logic"

NARRATIVE:
- If this chunk was derived from a narrative document, reference the narrative directory name.
- When setting this field during /chunk-create, also update the narrative's OVERVIEW.md
  frontmatter to add this chunk to its `chunks` array with the prompt and chunk_directory.
- If this is the final chunk of a narrative, the narrative status should be set to completed
  when this chunk is completed.

SUBSYSTEMS:
- Optional list of subsystem references that this chunk relates to
- Format: subsystem_id is {NNNN}-{short_name}, relationship is "implements" or "uses"
- "implements": This chunk directly implements part of the subsystem's functionality
- "uses": This chunk depends on or uses the subsystem's functionality
- Example:
  subsystems:
    - subsystem_id: "0001-validation"
      relationship: implements
    - subsystem_id: "0002-frontmatter"
      relationship: uses
- Validated by `ve chunk validate` to ensure referenced subsystems exist
- When a chunk that implements a subsystem is completed, a reference should be added to
  that chunk in the subsystems OVERVIEW.md file front matter and relevant section.
-->

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