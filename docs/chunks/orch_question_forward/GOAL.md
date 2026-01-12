---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after: ["created_after_clarity"]
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

CREATED_AFTER:
- Auto-populated by `ve chunk create` - DO NOT MODIFY manually
- Lists the "tips" of the chunk DAG at creation time (chunks with no dependents yet)
- Tips must be ACTIVE chunks (shipped work that has been merged)
- Example: created_after: ["auth_refactor", "api_cleanup"]

IMPORTANT - created_after is NOT implementation dependencies:
- created_after tracks CAUSAL ORDERING (what work existed when this chunk was created)
- It does NOT mean "chunks that must be implemented before this one can work"
- FUTURE chunks can NEVER be tips (they haven't shipped yet)

COMMON MISTAKE: Setting created_after to reference FUTURE chunks because they
represent design dependencies. This is WRONG. If chunk B conceptually depends on
chunk A's implementation, but A is still FUTURE, B's created_after should still
reference the current ACTIVE tips, not A.

WHERE TO TRACK IMPLEMENTATION DEPENDENCIES:
- Investigation proposed_chunks ordering (earlier = implement first)
- Narrative chunk sequencing in OVERVIEW.md
- Design documents describing the intended build order
- The `created_after` field will naturally reflect this once chunks ship
-->

# Chunk Goal

## Minor Goal

When background agents running under the orchestrator attempt to use the `AskUserQuestion` tool, forward those requests to the attention queue system rather than blocking or failing silently.

Currently, as discovered in the transcript audit, when background agents call `AskUserQuestion`, the tool returns an error (`is_error=True` with message "Answer questions?") and agents silently proceed without getting answers. This leads to unresolved uncertainty and potential implementation issues.

This chunk enables:
- Background agents to ask questions that surface in the attention queue
- Operators to answer agent questions via `ve orch answer` (from orch_attention_queue)
- Agent sessions to resume with the operator's answer injected
- Proper handling of uncertainty rather than silent failure

## Success Criteria

1. **AskUserQuestion calls are intercepted and forwarded**
   - When a background agent calls `AskUserQuestion`, the request is captured
   - The work unit transitions to NEEDS_ATTENTION status
   - The `attention_reason` field is populated with the question details
   - The agent session is paused (not terminated)

2. **Question context is preserved for operators**
   - Question text, options, and metadata are stored in the work unit
   - `ve orch attention` displays the question in the attention queue
   - Operators can see which agent asked what question and in what context

3. **Answers resume agent execution with context**
   - `ve orch answer <chunk> "response"` injects the answer into the session
   - The agent receives the answer as if the user had responded to `AskUserQuestion`
   - Work unit transitions: NEEDS_ATTENTION → RUNNING
   - Agent continues from where it paused, not from scratch

4. **Integration with Claude Code SDK**
   - Hook into Claude Code's tool handling to intercept `AskUserQuestion`
   - Use session resume capability with the answer injected as user message
   - Preserve session ID for resumption (from orch_attention_reason)

5. **Graceful handling of edge cases**
   - Multi-question tool calls are handled (all questions surfaced)
   - Agent timeout during NEEDS_ATTENTION doesn't lose context
   - Multiple agents asking questions simultaneously works correctly

## Dependencies

This chunk depends on:
- **orch_attention_queue** - Provides the attention queue infrastructure, `ve orch attention` and `ve orch answer` commands
- **orch_attention_reason** - Provides the `attention_reason` field and session_id tracking in work units

## Out of Scope

- Web dashboard for viewing/answering questions (Phase 5)
- Rich question UI beyond text answers
- Automatic answer generation or suggestions
- Question routing to specific operators