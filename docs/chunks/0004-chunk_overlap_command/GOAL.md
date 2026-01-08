---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/ve.py
  - src/chunks.py
  - tests/test_chunk_overlap.py
code_references:
  - file: src/ve.py
    ranges:
      - lines: 8
        implements: "pyyaml dependency for YAML frontmatter parsing"
      - lines: 141-155
        implements: "overlap CLI command - accepts chunk_id, --project-dir, outputs affected chunk paths"
  - file: src/chunks.py
    ranges:
      - lines: 7
        implements: "yaml import for frontmatter parsing"
      - lines: 88-102
        implements: "resolve_chunk_id() - resolves 4-digit or full name to directory name"
      - lines: 104-113
        implements: "get_chunk_goal_path() - resolves chunk ID to GOAL.md path"
      - lines: 115-136
        implements: "parse_chunk_frontmatter() - extracts and parses YAML frontmatter from GOAL.md"
      - lines: 138-171
        implements: "parse_code_references() - parses nested code_references format into file->line mappings"
      - lines: 173-242
        implements: "find_overlapping_chunks() - finds ACTIVE chunks with lower IDs having overlapping references"
  - file: tests/test_chunk_overlap.py
    ranges:
      - lines: 1-275
        implements: "TestOverlapCommand - 11 tests covering CLI interface, overlap detection, edge cases"
---

# Chunk Goal

## Minor Goal

Implement `ve chunk overlap <chunk_id>` to identify which ACTIVE chunks have code references that may have been affected by the specified chunk's changes. This supports the trunk GOAL.md's requirement that "maintaining the referential integrity of documents is an agent problem" by providing tooling to guide reference updates at chunk completion time.

When completing a chunk, knowing which other chunks have potentially-shifted references allows agents to systematically update those references rather than discovering drift later.

## Success Criteria

### Command Interface

- `ve chunk overlap <chunk_id>` command exists
- `chunk_id` accepts the 4-digit sequential ID (e.g., `0003`) or full directory name (e.g., `0003-my_feature`)
- Supports `--project-dir` option to specify target project
- Outputs list of relative paths to affected chunk directories (e.g., `docs/chunks/0001-feature`)

### Overlap Detection Logic

The key insight is that **chunk ordering determines causality**:

- Only ACTIVE chunks with IDs **lower than** the specified chunk can have affected references (chunks created before cannot be affected by chunks created after)
- A chunk Y (created before chunk X) is affected if:
  1. X has code references in a file that Y also references, AND
  2. X's earliest reference line in that file is **less than or equal to** Y's latest reference line in that file

This captures the scenario where X added/modified lines that would shift Y's line numbers downward.

### Output Format

- Lists affected chunk relative paths, one per line (e.g., `docs/chunks/0001-feature`)
- If no chunks are affected, outputs nothing (exit 0)
- If the specified chunk doesn't exist, outputs error and exits non-zero
- If the specified chunk has no code references, outputs nothing (exit 0)

### Edge Cases

- Handles chunks with empty `code_references` gracefully
- Handles chunks with `code_references: []` (explicit empty list)
- Handles chunks where referenced files no longer exist (still reports overlap based on metadata)
- Chunks with status other than ACTIVE are excluded from overlap detection