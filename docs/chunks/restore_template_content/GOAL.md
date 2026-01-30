---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/chunk-plan.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
code_references:
  - ref: src/templates/commands/chunk-plan.md.jinja2
    implements: "Cluster prefix suggestion step (Step 2) for semantic chunk naming"
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Investigation frontmatter reference, Proposed Chunks section, and Investigation lifecycle details"
narrative: null
investigation: template_drift
subsystems: []
created_after:
- xr_ve_worktrees_flag
- task_chunk_validation
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

Restore content that was lost from source templates due to the template drift pattern identified in the `template_drift` investigation. Agents previously edited rendered files (`.claude/commands/*.md`, `CLAUDE.md`) instead of source templates (`src/templates/`), and subsequent re-renders overwrote their work.

This chunk backports the lost content from git history to the source templates, ensuring future renders include the complete, intended content.

## Success Criteria

1. **chunk-plan.md.jinja2 restored**: The cluster prefix suggestion step is restored to `src/templates/commands/chunk-plan.md.jinja2` from commit `8a29e62`:
   - Step 2 runs `ve chunk suggest-prefix <chunk_name>` to check for semantic clustering
   - Presents suggestion to operator if prefix is found
   - Allows renaming before continuing

2. **CLAUDE.md.jinja2 restored**: The following sections are restored to `src/templates/claude/CLAUDE.md.jinja2` from commit `62b6d8f`:
   - `investigation` frontmatter reference in "Chunk Frontmatter References" section
   - "Proposed Chunks" section explaining the `proposed_chunks` frontmatter pattern
   - Correct prose linking "Proposed Chunks" to `proposed_chunks` frontmatter (not just "Chunks")
   - Investigation lifecycle details (status table, when to use)
   - "What Counts as Code" section (clarifying templates are code)
   - Development section (uv run instructions for ve developers)

3. **Re-render produces correct output**: Running template render produces `.claude/commands/chunk-plan.md` and `CLAUDE.md` with the restored content

## Git History References

Use these commits to extract the correct content:

- **`8a29e62`** - Contains cluster prefix suggestion for chunk-plan.md (`.claude/commands/chunk-plan.md` diff)
- **`62b6d8f`** - Contains proposed_chunks standardization for CLAUDE.md (`CLAUDE.md` diff)

Run `git show <commit> -- <file>` to extract the content that needs to be restored to the source templates.