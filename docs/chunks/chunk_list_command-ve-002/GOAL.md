---
status: ACTIVE
ticket: ve-002
parent_chunk: null
code_paths:
- src/ve.py
- src/chunks.py
- tests/test_ve.py
code_references:
- ref: src/chunks.py#Chunks::list_chunks
  implements: Lists chunks in causal order (newest first) using ArtifactIndex
- ref: src/chunks.py#Chunks::get_latest_chunk
  implements: Returns first chunk in causal order (newest)
- ref: src/ve.py#list_chunks
  implements: CLI command ve chunk list with --latest, --last-active, and --project-dir options
- ref: tests/test_chunks.py
  implements: Unit tests for list_chunks() and get_latest_chunk() methods
- ref: tests/test_chunk_list.py
  implements: CLI integration tests for ve chunk list
created_after:
- implement_chunk_start-ve-001
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