---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
created_after:
- narrative_backreference_support
- orch_inject_path_compat
- orch_submit_future_cmd
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

INVESTIGATION:
- If this chunk was derived from an investigation's proposed_chunks, reference the investigation
  directory name (e.g., "memory_leak" for docs/investigations/memory_leak/).
- This provides traceability from implementation work back to exploratory findings.
- When implementing, read the referenced investigation's OVERVIEW.md for context on findings,
  hypotheses tested, and decisions made during exploration.
- Validated by `ve chunk validate` to ensure referenced investigations exist.

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

Clarify the semantics of the `created_after` field in chunk GOAL.md templates to prevent agents from confusing **causal ordering** (what has shipped) with **implementation dependencies** (what must exist for this chunk to work).

**The problem**: Agents commonly misinterpret `created_after` as "chunks that must be implemented before this one can work" and incorrectly set it to reference FUTURE chunks. This happened when creating `orch_conflict_oracle` - it was incorrectly set to `["orch_attention_queue"]` (a FUTURE chunk) instead of the actual tips.

**The fix**: Update the GOAL.md template's comment block to explicitly contrast these concepts and guide agents to the correct behavior.

## Success Criteria

1. **Template updated**: The GOAL.md Jinja2 template (`src/templates/chunks/GOAL.md.jinja2`) includes clear documentation distinguishing:
   - `created_after` = causal ordering (the tips when this chunk was created; always references ACTIVE/shipped chunks)
   - Implementation dependencies = tracked elsewhere (investigation `proposed_chunks` order, design docs, narrative sequencing)

2. **Anti-pattern documented**: The template explicitly warns against setting `created_after` to FUTURE chunks

3. **Guidance on where to track design dependencies**: The template points agents to the correct places for sequencing future work

4. **Regenerated files updated**: Running `ve init` propagates the template changes to rendered GOAL.md files

