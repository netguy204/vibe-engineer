---
status: ACTIVE
ticket: ve-001
parent_chunk: null
code_paths:
  - src/ve.py
  - src/chunks.py
  - tests/test_ve.py
code_references:
  - ref: src/ve.py#validate_short_name
    implements: "Short name validation delegating to validate_identifier()"
  - ref: src/ve.py#validate_ticket_id
    implements: "Ticket ID validation delegating to validate_identifier()"
  - ref: src/ve.py#start
    implements: "start command - argument parsing, validation, normalization, duplicate detection, --yes flag"
  - ref: src/chunks.py#Chunks::__init__
    implements: "Chunks class initialization"
  - ref: src/chunks.py#Chunks::enumerate_chunks
    implements: "List existing chunk directories"
  - ref: src/chunks.py#Chunks::num_chunks
    implements: "Count of existing chunks"
  - ref: src/chunks.py#Chunks::find_duplicates
    implements: "Detects existing chunks with same short_name+ticket_id"
  - ref: src/chunks.py#Chunks::create_chunk
    implements: "Directory creation with correct path format, template rendering"
  - ref: tests/test_chunk_start.py
    implements: "Comprehensive test suite covering chunk start command"
---

<!--
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
-->

# Chunk Goal

## Minor Goal

Implement `ve chunk start short_name [ticket_id]` to create new chunk directories with rendered templates. This is foundational - without it, no other chunk workflows are possible.

## Success Criteria

### Command Interface

- `ve chunk start short_name [ticket_id]` command exists
- `short_name` is required, `ticket_id` is optional
- Supports `--project-dir` option to specify target project
- Supports `--yes` flag to skip confirmation prompts (for scripting/CI)

### Validation

- Short name rejects spaces (lists error)
- Short name rejects characters outside `[a-zA-Z0-9_-]`
- Short name rejects length >= 32 characters
- Short name normalized to lowercase
- All validation errors listed together in one message
- Ticket ID validated with same character rules when provided
- Ticket ID normalized to lowercase
- Exit non-zero on validation failure

### Directory Creation

- Creates chunk at `docs/chunks/{NNNN}-{short_name}-{ticket_id}/` when ticket provided
- Creates chunk at `docs/chunks/{NNNN}-{short_name}/` when ticket omitted
- Sequential ID (`NNNN`) auto-increments from existing chunks
- Creates `docs/chunks/` silently if it doesn't exist
- Prompts user if chunk with same short_name + ticket_id combo already exists

### Output and Templates

- On success, prints only the created path (e.g., `Created docs/chunks/0002-add_logging-ve-001/`)
- Renders GOAL.md, PLAN.md, TESTS.md from templates into the new chunk directory
- Templates receive context: `ticket_id`, `short_name`, `next_chunk_id`