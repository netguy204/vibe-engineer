---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
  - src/templates/chunk/GOAL.md
  - tests/test_chunks.py
code_references: []
narrative: null
---
<!--
DO NOT DELETE THIS COMMENT until the chunk complete command is run.
This describes schema information that needs to be adhered
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
-->

# Chunk Goal

## Minor Goal

Fix the chunk GOAL.md template to output valid YAML `null` instead of Python's `None` when no ticket ID is provided.

Currently, `src/templates/chunk/GOAL.md` uses `{{ ticket_id }}` which renders Python's `None` value as the literal string `None`. YAML interprets this as the string "None" rather than a null value, producing invalid frontmatter.

This advances the trunk goal's **Required Properties** by ensuring generated artifacts are immediately valid without manual correction—a prerequisite for maintaining document health over time.

## Success Criteria

1. **Template uses Jinja2 filter** to convert Python `None` to YAML `null`:
   - Change `ticket: {{ ticket_id }}` to `ticket: {{ ticket_id | default('null', true) }}` or equivalent
   - The `default` filter with `true` as second argument treats `None` as undefined

2. **New chunks render valid YAML**:
   - Running `ve chunk start test_chunk` produces `ticket: null` (not `ticket: None`)
   - Running `ve chunk start test_chunk TICKET-123` produces `ticket: TICKET-123`

3. **Unit test** verifies both cases:
   - Template renders `null` when ticket_id is None
   - Template renders the ticket ID when provided