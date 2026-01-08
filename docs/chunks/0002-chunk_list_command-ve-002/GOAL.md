---
status: ACTIVE
ticket: ve-002
parent_chunk: null
code_paths:
  - src/ve.py
  - src/chunks.py
  - tests/test_ve.py
code_references:
  - file: src/chunks.py
    ranges:
      - lines: 52-67
        implements: "list_chunks() method - lists chunks sorted by numeric prefix descending"
      - lines: 69-78
        implements: "get_latest_chunk() method - returns highest-numbered chunk"
  - file: src/ve.py
    ranges:
      - lines: 111-129
        implements: "list CLI command - ve chunk list with --latest and --project-dir options"
  - file: tests/test_chunks.py
    ranges:
      - lines: 35-71
        implements: "TestListChunks - unit tests for list_chunks() method"
      - lines: 74-95
        implements: "TestGetLatestChunk - unit tests for get_latest_chunk() method"
  - file: tests/test_chunk_list.py
    ranges:
      - lines: 6-93
        implements: "TestListCommand - CLI integration tests for ve chunk list"
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