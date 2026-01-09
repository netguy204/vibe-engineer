---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
subsystems: []
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
- If this is the final chunk of a narrative, the narrative status should be set to completed 
  when this chunk is completed. 

SUBSYSTEMS:
- Optional list of subsystem references that this chunk relates to
- Format: subsystem_id is {NNNN}-{short_name}, relationship is "implements" or "uses"
- "implements": This chunk directly implements part of the subsystem's functionality
- "uses": This chunk depends on or uses the subsystem's functionality
- Example:
  subsystems:
    - subsystem_id: "0001-validation"
      relationship: implements
    - subsystem_id: "0002-frontmatter"
      relationship: uses
- Validated by `ve chunk validate` to ensure referenced subsystems exist
- When a chunk that implements a subsystem is completed, a reference should be added to
  that chunk in the subsystems OVERVIEW.md file front matter and relevant section. 
-->

# Chunk Goal

## Minor Goal

Fix the chunk sequence number calculation bug in `src/chunks.py` that causes duplicate chunk numbers when there are gaps in the sequence.

The current implementation uses `num_chunks + 1` (count of chunks) instead of `max_chunk_number + 1`. When chunks are deleted or misnumbered, this causes collisions. For example, if chunks 0001-0025 and 0027 exist (26 total), the next chunk incorrectly gets numbered 0027 instead of 0028.

This advances the project's correctness constraints by ensuring chunk numbering is always unique and monotonically increasing.

## Success Criteria

1. **Bug fixed**: `create_chunk()` in `src/chunks.py` uses the maximum existing chunk number + 1 instead of the count + 1.

2. **Edge cases handled**:
   - Empty chunks directory returns 0001
   - Gaps in sequence are tolerated (next number is always max + 1)
   - Non-numeric prefixes are ignored

3. **Tests pass**: Existing tests continue to pass, and a new test verifies correct behavior with gaps in the sequence.

4. **No duplicate detection needed**: The fix prevents duplicates by construction; no need to add collision detection.