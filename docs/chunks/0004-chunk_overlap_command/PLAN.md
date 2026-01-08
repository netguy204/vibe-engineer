# Implementation Plan

## Approach

We build `ve chunk overlap <chunk_id>` following the established CLI patterns in `ve.py` (view layer) and `chunks.py` (business logic). The command parses chunk frontmatter to extract `code_references`, then applies the overlap detection algorithm defined in GOAL.md.

Following DEC-001 (uvx-based CLI), the command integrates into the existing Click command group. Following TESTING_PHILOSOPHY.md, we write failing tests first that assert semantic behavior (affected chunk names, exit codes) rather than structural properties.

The overlap detection logic:
1. Parse the target chunk's `code_references` from its GOAL.md frontmatter
2. Find all ACTIVE chunks with IDs **lower than** the target
3. For each candidate chunk, check if any of its references overlap with the target's references in the same file
4. Two chunks overlap if: target's earliest line in a file ≤ candidate's latest line in that file

## Sequence

### Step 1: Write failing CLI tests

Create `tests/test_chunk_overlap.py` with tests covering the success criteria:

- `--help` shows correct usage
- Non-existent chunk ID exits non-zero with error message
- Chunk with no code_references outputs nothing, exits 0
- No ACTIVE chunks with lower IDs outputs nothing, exits 0
- Chunk with overlapping references outputs affected chunk relative paths
- Chunk ID accepts both 4-digit form (`0003`) and full directory name
- `--project-dir` option works correctly

Location: `tests/test_chunk_overlap.py`

### Step 2: Add frontmatter parsing to Chunks class

Add methods to the `Chunks` class to:
- `get_chunk_goal_path(chunk_id)` - resolve chunk ID to GOAL.md path
- `parse_chunk_frontmatter(chunk_id)` - parse YAML frontmatter from GOAL.md

Use Python's `re` for frontmatter extraction and built-in YAML parsing via the already-available jinja2 dependency won't work—add `pyyaml` to script dependencies.

Location: `src/chunks.py`

### Step 3: Implement overlap detection in Chunks class

Add method `find_overlapping_chunks(chunk_id)` that:
1. Validates chunk_id exists (raises ValueError if not)
2. Parses target chunk's frontmatter to get `code_references`
3. If no code_references, returns empty list
4. Finds all ACTIVE chunks with lower numeric IDs
5. For each candidate, checks overlap condition
6. Returns list of affected chunk relative paths (e.g., `docs/chunks/0001-feature`)

Location: `src/chunks.py`

### Step 4: Add CLI command

Add `overlap` subcommand to the `chunk` group in `ve.py`:
- Accept `chunk_id` argument (4-digit or full name)
- Accept `--project-dir` option
- Call `chunks.find_overlapping_chunks()`
- Output affected chunk relative paths (one per line) or nothing
- Exit 0 on success, 1 on error

Location: `src/ve.py`

### Step 5: Verify tests pass

Run `pytest tests/test_chunk_overlap.py` to confirm all tests pass.

## Dependencies

- Requires adding `pyyaml` to the script dependencies in `ve.py`
- No chunk dependencies (builds on existing chunk infrastructure from 0001-0003)

## Risks and Open Questions

- **YAML parsing edge cases**: Frontmatter might have unusual formatting. We'll handle this by being defensive in parsing and treating malformed frontmatter as "no references."
- **Chunk ID resolution ambiguity**: If user passes `0003` but multiple directories start with `0003-`, we match the first. The GOAL.md specifies accepting both forms, so we implement exact-prefix matching.

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