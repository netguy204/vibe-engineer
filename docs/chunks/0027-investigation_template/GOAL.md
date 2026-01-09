---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: 0003-investigations
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

Create the investigation OVERVIEW.md template in `src/templates/investigation/`, establishing investigations as a first-class artifact type in the vibe engineering workflow.

This advances the Problem Statement's core thesis (docs/trunk/GOAL.md) that understanding the goal and correctness constraints is the engineering problem. Investigations provide a structured way to explore unknowns—whether issues in the system or potential new concepts—before committing to implementation. They capture the learning process itself, ensuring that even "no action" decisions are documented and defensible.

Unlike narratives (which start with a known ambition and decompose into chunks) or subsystems (which document emergent patterns), investigations start with uncertainty. They may or may not produce chunks. The value is in the structured exploration and the captured learning.

## Success Criteria

1. **Template exists** at `src/templates/investigation/OVERVIEW.md.jinja2` following the established Jinja2 template patterns used by narrative and subsystem templates.

2. **Frontmatter schema** includes:
   - `status`: ONGOING | SOLVED | NOTED | DEFERRED
   - `trigger`: Brief description of what prompted the investigation
   - `proposed_chunks`: Array for chunk prompts (similar to narrative's chunks array)

3. **Required sections** are present with appropriate guidance comments:
   - **Trigger** - What prompted this investigation (problem or opportunity)
   - **Success Criteria** - How we'll know the investigation is complete
   - **Testable Hypotheses** - Encourages objective verification where possible
   - **Exploration Log** - Timestamped record of exploration steps and findings
   - **Findings** - Verified findings vs opinions/hypotheses distinction
   - **Proposed Chunks** - Chunk prompts if action is warranted (like narrative chunks)
   - **Resolution Rationale** - Why the chosen outcome (SOLVED/NOTED/DEFERRED)

4. **Template guidance** should:
   - Nudge toward identifying testable hypotheses
   - Encourage objective verification (measurements, prototypes, spikes)
   - Distinguish between verified findings and opinions/hypotheses
   - Not mandate structural distinction between "issue" and "concept" investigations (the trigger naturally captures this)

5. **Pattern consistency** with existing templates—uses similar comment block style for schema documentation and discovery prompts as seen in `narrative/OVERVIEW.md.jinja2` and `subsystem/OVERVIEW.md.jinja2`.