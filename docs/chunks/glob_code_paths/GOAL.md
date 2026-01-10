---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
subsystems: []
created_after: ["update_crossref_format"]
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

Add glob pattern support to the `code_paths` frontmatter field for chunk overlap detection.

Currently, `code_paths` expects literal file paths (e.g., `src/chunks.py`), but for chunks
that touch many files following a pattern, glob syntax (e.g., `src/**/*.py`) is more
expressive and maintainable.

This is the right next step because:

1. **Natural expression of broad changes** - Some chunks (like migrations or refactors)
   touch many files matching a pattern. Listing each file individually is tedious and
   error-prone. Glob patterns like `src/**/*.py` capture the intent clearly.

2. **Consistency with common tooling** - Developers are familiar with glob patterns from
   `.gitignore`, editor configs, and build tools. Supporting them here reduces friction.

3. **Enables accurate overlap detection** - Without glob support, chunks that touch "all
   Python files" either list incomplete paths or skip `code_paths` entirely, weakening
   overlap detection.

## Success Criteria

1. **Glob patterns expand correctly** - `code_paths` entries containing glob characters
   (`*`, `**`, `?`, `[...]`) are expanded to matching files when computing overlap.

2. **Literal paths still work** - Non-glob entries continue to work as before (exact
   file path matching).

3. **Overlap detection uses expanded paths** - When checking for overlapping chunks,
   glob patterns in `code_paths` are expanded and compared against other chunks'
   expanded paths.

4. **Validation handles globs** - `ve chunk validate` correctly handles glob patterns
   in `code_paths` (warns if pattern matches no files, etc.).

5. **Template documentation updated** - The GOAL.md template's `CODE_PATHS` comment
   documents that glob patterns are supported.

6. **Tests cover glob behavior** - Unit tests verify glob expansion and overlap
   detection with glob patterns.