---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/chunks.py
- tests/test_chunk_start.py
code_references:
  - ref: src/chunks.py#Chunks::create_chunk
    implements: "Guard logic preventing multiple IMPLEMENTING chunks"
  - ref: tests/test_chunk_start.py#TestImplementingGuard
    implements: "Test coverage for IMPLEMENTING guard behavior"
narrative: null
subsystems: []
created_after:
- external_chunk_causal
---

# Chunk Goal

## Minor Goal

The `ve chunk start` command should fail with a clear error message if there is already a chunk with status `IMPLEMENTING`. This prevents workflow inconsistency where an operator forgets to transition a chunk to `ACTIVE` before starting new work, which would leave multiple chunks in progress and create ambiguity about what work is current.

This supports the workflow invariant that exactly one chunk should be in `IMPLEMENTING` status at any time, ensuring clear ownership of active work.

## Success Criteria

- `ve chunk start <name>` fails with a descriptive error when an `IMPLEMENTING` chunk already exists
- `ve chunk activate <name>` fails with a descriptive error when an `IMPLEMENTING` chunk already exists
- Error messages identify the existing IMPLEMENTING chunk by name/path
- Error messages suggest running `ve chunk complete` first to transition the current work
- The `--future` flag on `ve chunk start` bypasses the check (since FUTURE chunks don't conflict)
- Existing tests continue to pass
- New test cases cover both guard behaviors

