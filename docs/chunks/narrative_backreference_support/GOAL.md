---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: chunk_reference_decay
subsystems: []
created_after: ["chunk_create_guard", "orch_attention_reason", "orch_inject_validate", "deferred_worktree_creation"]
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

Add narrative backreference support to source code files, enabling code to reference narrative documents that provide architectural context about why the code exists. This complements the existing `# Chunk:` and `# Subsystem:` backreference patterns.

**Why this matters**: The chunk_reference_decay investigation found that chunk backreferences accumulate over time and provide diminishing semantic value for understanding code PURPOSE. Narratives synthesize the "why" across multiple chunks into a coherent story. When code can reference a narrative, agents get architectural context immediately rather than piecing together fragments from multiple chunk GOALs.

**Format**: `# Narrative: docs/narratives/{directory_name} - {optional description}`

**Example**:
```python
# Narrative: docs/narratives/chunk_lifecycle_management - Core lifecycle infrastructure
# Chunk: docs/chunks/symbolic_code_refs - Symbol extraction and parsing
def enumerate_chunks():
    ...
```

## Success Criteria

1. **Parser recognizes narrative backreferences**: The backreference parsing code (likely in a symbols or parsing module) can extract `# Narrative:` comments from source files, similar to how `# Chunk:` and `# Subsystem:` are handled.

2. **CLAUDE.md documents the narrative backreference format**: The template for CLAUDE.md includes documentation of the `# Narrative:` backreference pattern alongside the existing chunk and subsystem patterns.

3. **Validation exists for narrative references**: When a source file references a narrative (e.g., `# Narrative: docs/narratives/foo`), there's validation that the referenced narrative directory exists, similar to chunk/subsystem reference validation.

4. **Tests cover narrative backreference parsing**: Unit tests verify that narrative backreferences are correctly extracted from source files.

5. **Backreference priority is clear**: Documentation clarifies the semantic hierarchy: narratives provide PURPOSE context (why the code exists architecturally), chunks provide HISTORY context (what work created/modified the code), subsystems provide PATTERN context (what rules govern the code).

