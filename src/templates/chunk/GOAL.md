---
status: {{ status | default('IMPLEMENTING') }}
ticket: {{ ticket_id }}
parent_chunk: null
code_paths: []
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

<!--
What does this chunk accomplish? Frame it in terms of docs/trunk/GOAL.md.
Why is this the right next step? What does completing this enable?

Keep this focused. If you're describing multiple independent outcomes,
you may need multiple chunks.
-->

## Success Criteria

<!--
How will you know this chunk is done? Be specific and verifiable.
Reference relevant sections of docs/trunk/SPEC.md where applicable.

Example:
- SegmentWriter correctly encodes messages per SPEC.md Section 3.2
- fsync is called after each write, satisfying durability guarantee
- Write throughput meets SPEC.md performance requirements (>50K msg/sec)
- All tests in TESTS.md pass
-->

## Relationship to Parent

<!--
DELETE THIS SECTION if parent_chunk is null.

If this chunk modifies work from a previous chunk, explain:
- What deficiency or change prompted this work?
- What from the parent chunk remains valid?
- What is being changed and why?

This context helps agents understand the delta and avoid breaking
invariants established by the parent.
-->