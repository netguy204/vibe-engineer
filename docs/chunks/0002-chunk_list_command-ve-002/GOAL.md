---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/ve.py
  - src/chunks.py
  - tests/test_ve.py
code_references:
  - src/chunks.py:39-54  # list_chunks() method - lists chunks sorted by numeric prefix descending
  - src/chunks.py:56-65  # get_latest_chunk() method - returns highest-numbered chunk
  - src/ve.py:108-125  # list CLI command - ve chunk list with --latest and --project-dir options
  - tests/test_ve.py:300-336  # TestListChunks - unit tests for list_chunks() method
  - tests/test_ve.py:339-359  # TestGetLatestChunk - unit tests for get_latest_chunk() method
  - tests/test_ve.py:362-448  # TestListCommand - CLI integration tests for ve chunk list
---

# Chunk Goal

## Minor Goal

Implement `ve chunk list` command to enumerate existing chunks. This provides visibility into what chunks exist in a project and enables scripts/tooling to programmatically find the latest chunk for automation workflows.

## Success Criteria

### Command Interface

- `ve chunk list` command exists
- Supports `--latest` flag to return only the most recent chunk
- Supports `--project-dir` option to specify target project (consistent with `start` command)

### Default Behavior (no flags)

- Lists all chunks in reverse numeric order (highest-numbered first)
- Each chunk displayed as its relative path from project root (e.g., `docs/chunks/0002-chunk_list_command`)
- One chunk per line
- Exit code 0 on success

### `--latest` Behavior

- Returns only the relative path to the highest-numbered chunk directory
- "Highest-numbered" determined by the `NNNN` prefix in the directory name
- Single line of output, no trailing decoration
- Exit code 0 on success

### Empty State

- When no chunks exist, prints "No chunks found" to stderr
- Exit code 1

### Examples

```bash
# List all chunks (reverse order)
$ ve chunk list
docs/chunks/0002-chunk_list_command
docs/chunks/0001-implement_chunk_start-ve-001

# Get latest chunk path
$ ve chunk list --latest
docs/chunks/0002-chunk_list_command

# Empty project
$ ve chunk list
No chunks found
$ echo $?
1
```