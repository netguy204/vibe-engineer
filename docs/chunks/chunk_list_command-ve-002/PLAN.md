---
status: ACTIVE
---

# Implementation Plan

## Approach

Build the `ve chunk list` command following the existing patterns established in
chunk 0001 (`ve chunk start`). The implementation will:

1. **Extend the `Chunks` class** in `src/chunks.py` with a method to list chunks
   in sorted order, extracting the numeric prefix for proper ordering.

2. **Add a new Click subcommand** under the existing `chunk` group in
   `src/ve.py`, following the same option patterns (`--project-dir`) as the
   `start` command.

3. **Follow the view/business-logic separation** already established: CLI layer
   handles presentation and options, `Chunks` class handles the logic.

This approach builds on DEC-001 (uvx-based CLI utility) and maintains
consistency with the existing codebase.

## Sequence

### Step 1: Add `list_chunks()` method to Chunks class

Add a method to `Chunks` class that returns chunk directory names sorted by
their numeric prefix (highest first).

**Location**: `src/chunks.py`

**Inputs**: None (uses `self.chunk_dir`)

**Outputs**: List of `(chunk_number: int, chunk_name: str)` tuples, sorted by
chunk_number descending. Returns empty list if no chunks exist.

**Implementation details**:
- Iterate over `self.chunk_dir` directories
- Parse the `NNNN` prefix from each directory name using regex
- Sort by numeric prefix descending
- Return list of tuples for flexibility (CLI can access number or path as
  needed)

### Step 2: Add `get_latest_chunk()` method to Chunks class

Add a convenience method that returns only the highest-numbered chunk.

**Location**: `src/chunks.py`

**Inputs**: None

**Outputs**: `str | None` - chunk directory name if exists, None otherwise

**Implementation details**:
- Call `list_chunks()`
- Return first item's name if list is non-empty, else None

### Step 3: Add `list` subcommand to CLI

Add the `list` command under the `chunk` group.

**Location**: `src/ve.py`

**Options**:
- `--latest` flag: If set, output only the most recent chunk
- `--project-dir`: Same as `start` command, defaults to current directory

**Behavior**:
- Create `Chunks` instance with `project_dir`
- Call `list_chunks()` to get sorted chunks
- If no chunks: print "No chunks found" to stderr, exit 1
- If `--latest`: print relative path of first (highest-numbered) chunk
- Else: print each chunk's relative path, one per line

### Step 4: Write unit tests for `Chunks.list_chunks()`

**Location**: `tests/test_ve.py`

**Test cases**:
- Empty project returns empty list
- Single chunk returns list with one item
- Multiple chunks returned in descending numeric order
- Chunks with different name formats (with/without ticket_id) all parsed
  correctly

### Step 5: Write unit tests for `Chunks.get_latest_chunk()`

**Location**: `tests/test_ve.py`

**Test cases**:
- Empty project returns None
- Single chunk returns that chunk's name
- Multiple chunks returns highest-numbered chunk

### Step 6: Write CLI integration tests for `ve chunk list`

**Location**: `tests/test_ve.py`

**Test cases**:
- `--help` shows correct usage
- Empty project: stderr says "No chunks found", exit code 1
- Single chunk: outputs relative path, exit code 0
- Multiple chunks: outputs in reverse numeric order, exit code 0
- `--latest` with multiple chunks: outputs only highest-numbered chunk
- `--project-dir` option works correctly

### Step 7: Verify end-to-end behavior

Run the full test suite and manually verify the command works as specified in
the goal's examples.

## Dependencies

- Chunk 0001 must be complete (provides the `Chunks` class and `start` command)
  - **Status**: Complete

## Risks and Open Questions

- **Parsing edge cases**: Directory names that don't match the expected
  `NNNN-*` pattern could cause issues. The `list_chunks()` method should skip
  directories that don't start with a 4-digit prefix rather than failing.

- **Performance with many chunks**: Current approach loads all chunk names into
  memory. This is fine for expected usage (tens to low hundreds of chunks). If
  performance becomes an issue with thousands of chunks, could add generator
  pattern, but premature optimization is not warranted now.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
