---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
subsystems: []
created_after: ["investigation_chunk_refs"]
---

<!--
╔══════════════════════════════════════════════════════════════════════════════╗
║  DO NOT DELETE THIS COMMENT BLOCK until the chunk complete command is run.   ║
║                                                                              ║
║  AGENT INSTRUCTIONS: When editing this file, preserve this entire comment    ║
║  block. Only modify the frontmatter YAML and the content sections below      ║
║  (Minor Goal, Success Criteria, Relationship to Parent). Use targeted edits  ║
║  that replace specific sections rather than rewriting the entire file.       ║
╚══════════════════════════════════════════════════════════════════════════════╝

This comment describes schema information that needs to be adhered
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

CHUNK ARTIFACTS:
- Single-use scripts, migration tools, or one-time utilities created for this chunk
  should be stored in the chunk directory (e.g., docs/chunks/0042-foo/migrate.py)
- These artifacts help future archaeologists understand what the chunk did
- Unlike code in src/, chunk artifacts are not expected to be maintained long-term
- Examples: data migration scripts, one-time fixups, analysis tools used during implementation
-->

# Chunk Goal

## Minor Goal

The `/chunk-create` slash command currently has rigid logic for determining whether to create a FUTURE or IMPLEMENTING chunk: it only uses `--future` when an implementing chunk already exists. This ignores explicit user intent when they say things like "create this for the future" or "queue this up for later."

This chunk improves the slash command to analyze the user's input for explicit signals about timing preference, giving those signals priority over the default heuristics. This respects user autonomy and makes the workflow more flexible.

## Success Criteria

1. **User intent detection**: The `/chunk-create` slash command instructions explicitly tell the agent to scan for user signals indicating FUTURE preference (e.g., "future", "later", "queue", "backlog", "upcoming", "not now", "after current work")
2. **Priority order documented**: Instructions clearly state: (1) explicit user signals take priority, (2) then check for existing implementing chunk, (3) then use default behavior
3. **IMPLEMENTING intent detection**: Also detect explicit "now", "immediately", "start working on", "next up" signals that indicate the user wants IMPLEMENTING status even when a chunk already exists
4. **Conflict handling**: If user intent conflicts with current state (e.g., "work on this now" but implementing chunk exists), the agent offers to pause the current implementing chunk so the new chunk can become IMPLEMENTING
5. **Safe pause protocol**: Before pausing an implementing chunk, the agent must:
   - Run tests and confirm they pass (gate the transition on healthy codebase)
   - Add a "Paused State" section to the chunk's PLAN.md documenting: what's been completed, what remains, any work-in-progress context the resuming agent needs
   - Only then change the chunk status from IMPLEMENTING to FUTURE

