---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: 0002-subsystem_documentation
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
-->

# Chunk Goal

## Minor Goal

Document subsystems as a first-class artifact type in the vibe engineering workflow. Update SPEC.md and the CLAUDE.md template so that operators and agents understand how to discover, document, and reference subsystems.

This is chunk 7 of the subsystem documentation narrative. It captures all the prior work (schemas, CLI commands, templates, bidirectional references, status transitions, discovery command) in the authoritative specification and user-facing documentation.

## Success Criteria

1. **SPEC.md updates**:
   - Add "Subsystem" to the Artifacts terminology section
   - Document `docs/subsystems/` directory structure (mirroring the chunks section)
   - Define subsystem OVERVIEW.md frontmatter schema (status, chunks, code_references)
   - Document subsystem status enum values (DISCOVERING, DOCUMENTED, REFACTORING, STABLE, DEPRECATED) with their meanings and agent behavior implications
   - Document chunk-subsystem relationship types (implements/uses)
   - Add subsystem CLI commands to API Surface section: `ve subsystem discover`, `ve subsystem list`, `ve subsystem status`

2. **CLAUDE.md template updates**:
   - Add a "Subsystems (`docs/subsystems/`)" section explaining what subsystems are and when to check them
   - Include guidance to check `docs/subsystems/` before implementing patterns that might already exist
   - Add `/subsystem-discover` to the Available Commands section

3. **Consistency**:
   - Frontmatter schema in SPEC.md matches the actual Pydantic models in `src/ve/subsystems.py`
   - CLI command documentation matches actual implementation