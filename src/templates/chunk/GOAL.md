---
status: IMPLEMENTING
ticket: {{ ticket_id }}
parent_chunk: null
code_paths: []
code_references: []
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

<!--
What does this chunk accomplish? Frame it in terms of the trunk GOAL.md.
Why is this the right next step? What does completing this enable?

Keep this focused. If you're describing multiple independent outcomes,
you may need multiple chunks.
-->

## Success Criteria

<!--
How will you know this chunk is done? Be specific and verifiable.
Reference relevant sections of trunk SPEC.md where applicable.

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