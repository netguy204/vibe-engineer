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

Standardize how proposed chunks are tracked across all artifact types (narratives, subsystems, and investigations) by migrating to a consistent `proposed_chunks` frontmatter format. This enables the set of proposed-but-not-yet-created chunks to be computable data, allowing new CLI commands to list pending work across the entire system.

Currently, investigations use a `proposed_chunks` array in frontmatter with `{prompt, chunk_directory}` entries. Narratives and subsystems track proposed work differently:
- Narratives have a `chunks` array, but this name doesn't convey that the chunks may not exist yet
- Subsystems describe proposed consolidation work in prose (the "Consolidation Chunks" section) rather than structured frontmatter

This chunk unifies these approaches by standardizing on `proposed_chunks` as the field name across all artifact types, clearly signaling that these are proposals that may or may not be implemented.

## Success Criteria

1. **Narrative template updated**:
   - Rename `chunks` to `proposed_chunks` in `src/templates/narrative/OVERVIEW.md.jinja2` frontmatter
   - Use consistent `{prompt, chunk_directory}` format matching investigations
   - Update template comments to reflect the new naming

2. **Subsystem template updated**:
   - Add `proposed_chunks` array in `src/templates/subsystem/OVERVIEW.md.jinja2` frontmatter for consolidation work
   - Keep existing `chunks` array for tracking already-created chunk relationships (implements/uses)
   - Migrate the prose "Consolidation Chunks" section guidance to reference the frontmatter array

3. **CLI command added**:
   - `ve chunk list-proposed` (or similar) lists all proposed chunks across investigations, narratives, and subsystems
   - Filters to entries where `chunk_directory` is null/empty (not yet created)
   - Shows source artifact (which investigation/narrative/subsystem proposed it)

4. **Existing artifacts migrated**:
   - Any existing narrative documents have `chunks` renamed to `proposed_chunks`
   - Any existing subsystem documents with proposed consolidation work in prose are migrated to the frontmatter array

5. **Documentation updated**:
   - CLAUDE.md explains the `proposed_chunks` pattern as a cross-cutting concept
   - Documents the new `ve chunk list-proposed` command