---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after: ["orch_attention_reason"]
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

Build the attention queue system for the orchestrator - a prioritized list of work units needing operator input, with CLI commands to view and respond to them.

This is Phase 3 from `docs/investigations/parallel_agent_orchestration/design.md`. Building on the scheduling layer (orch_scheduling) and attention reason tracking (orch_attention_reason), this chunk adds the operator-facing UX for managing blocked work. The attention queue is the "interrupt vector" in the OS analogy - when work units need operator decisions, they surface here prioritized by downstream impact.

This chunk enables:
- A prioritized view of all NEEDS_ATTENTION work units
- `ve orch attention` command to show the queue with context
- `ve orch answer` command to respond to agent questions and resume execution
- Priority scoring based on how many other work units are blocked
- Clear visibility into what's blocking parallel progress

## Success Criteria

1. **Attention queue shows NEEDS_ATTENTION work units with priority**
   - `ve orch attention` lists work units in priority order
   - Priority calculated by: blocked_chunk_count + (depth_in_graph * weight)
   - Tie-breaker: time in queue (older items surface first)
   - Each item shows: chunk name, reason, time waiting, blocks count

2. **Attention items display context for decision-making**
   - Question/decision text from `attention_reason` field
   - Phase the work unit is in (GOAL/PLAN/IMPLEMENT/COMPLETE)
   - How many other work units are blocked waiting on this one
   - Summary of chunk goal for context

3. **`ve orch answer` responds to questions and resumes agents**
   - `ve orch answer <chunk> "response text"` answers and resumes
   - Response is injected into the agent session on resume
   - Work unit transitions: NEEDS_ATTENTION → RUNNING
   - Session resumes using saved `session_id` with `options.resume`
   - Error if work unit is not in NEEDS_ATTENTION state

4. **API endpoints support the attention queue**
   - `GET /attention` returns prioritized queue with item details
   - `POST /work-units/{chunk}/answer` submits answer and triggers resume
   - Response includes updated work unit status

5. **Priority scoring reflects downstream impact**
   - Compute `blocked_by` graph from work unit dependencies
   - Count how many work units are transitively blocked by each attention item
   - Higher blocked count = higher priority (surface items that unblock the most work)

## Out of Scope

- Conflict detection between work units (Phase 4: Conflict Oracle)
- Web dashboard (Phase 5: Dashboard)
- Skip/defer functionality for attention items (can be added later)
- Review gates (auto-advance vs require-review decisions)
- Rich question types beyond simple text answers