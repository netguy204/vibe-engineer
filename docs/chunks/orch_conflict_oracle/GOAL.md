---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after: ["orch_inject_path_compat", "orch_submit_future_cmd"]
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

Implement the **Conflict Oracle** - a progressive analysis system that determines whether chunks can be safely parallelized or must be serialized. The oracle provides goal-level semantic comparison, plan-level file/symbol analysis, and surfaces uncertain conflicts to the operator for judgment via `ve orch resolve`.

This chunk enables the orchestrator to make intelligent scheduling decisions about parallel work. Without conflict detection, the orchestrator would either serialize all work (sacrificing throughput) or parallelize blindly (causing merge conflicts). The conflict oracle provides the judgment layer that balances throughput against merge safety.

## Success Criteria

1. **Progressive analysis at each stage**:
   - PROPOSED: LLM semantic comparison of chunk prompts
   - GOAL exists: LLM comparison of intent + scope from GOAL.md
   - PLAN exists: File overlap detection via `Location:` lines + LLM symbol prediction
   - COMPLETED: Exact symbol overlap from `code_references` frontmatter

2. **Three-way verdict system**: `should_serialize(chunk_a, chunk_b)` returns:
   - `INDEPENDENT` (confidence > 0.8 no overlap) - parallelize freely
   - `SERIALIZE` (confidence > 0.8 overlap) - must sequence
   - `ASK_OPERATOR` (uncertain) - queue attention item for operator judgment

3. **Symbol-level granularity**: Analysis considers symbol overlap (e.g., `src/ve.py#suggest_prefix_cmd` vs `src/ve.py#cluster_rename_cmd`), not just file overlap

4. **`ve orch resolve` command**: Allows operator to resolve uncertain conflicts with `parallelize` or `serialize` verdicts

5. **Integration with scheduler**: Blocked work units have `blocked_by` populated based on oracle verdicts; verdicts re-evaluated as chunks advance through lifecycle

6. **Tests pass**: Unit tests for conflict analysis at each stage; integration tests for scheduler interaction

