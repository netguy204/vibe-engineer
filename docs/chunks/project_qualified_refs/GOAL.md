---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: ["src/symbols.py", "src/models.py", "src/chunks.py", "src/subsystems.py", "tests/test_symbols.py", "tests/test_models.py"]
code_references:
  - ref: src/symbols.py#parse_reference
    implements: "Extended parsing to return 3-tuple (project, file_path, symbol_path) with project qualification support"
  - ref: src/symbols.py#qualify_ref
    implements: "New function to ensure refs are project-qualified before comparison"
  - ref: src/symbols.py#is_parent_of
    implements: "Extended to compare projects first, different projects never overlap"
  - ref: src/models.py#SymbolicReference::validate_ref
    implements: "Extended validation to accept org/repo::path format using _require_valid_repo_ref"
  - ref: src/chunks.py#compute_symbolic_overlap
    implements: "Updated to qualify refs with project context before comparison"
  - ref: src/chunks.py#Chunks::_validate_symbol_exists
    implements: "Updated to qualify refs before parsing"
  - ref: src/chunks.py#Chunks::find_overlapping_chunks
    implements: "Updated to use local project context for ref qualification"
  - ref: src/subsystems.py#Subsystems::_find_overlapping_refs
    implements: "Updated to qualify refs before comparison"
  - ref: tests/test_symbols.py#TestParseReferenceWithProjectQualification
    implements: "Unit tests for project-qualified reference parsing"
  - ref: tests/test_symbols.py#TestIsParentOfWithProjectContext
    implements: "Unit tests for is_parent_of with project context"
  - ref: tests/test_symbols.py#TestOverlapDetectionAcrossProjects
    implements: "Integration tests for overlap detection across projects"
  - ref: tests/test_models.py#TestSymbolicReferenceWithProjectQualification
    implements: "Unit tests for SymbolicReference validation with project qualification"
narrative: null
subsystems: []
created_after: ["task_aware_investigations", "task_aware_subsystem_cmds"]
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

Extend the `SymbolicReference` model to support project-qualified paths using the format `org/repo::path#symbol`. This enables task-level chunks (stored in an external artifact repo) to have forward code references pointing to code in multiple participating projects.

Currently, `SymbolicReference` only supports local file paths like `src/foo.py#FooClass`. When working in a task context that spans multiple repositories, chunk completion (`/chunk-complete`) needs to collect code references from ALL participating projects and store them with project qualification so readers know which project each reference belongs to.

This directly supports the project goal of enabling multi-project workflows. Without project-qualified references, task-level chunks cannot properly document which code they touch across repositories, breaking the bidirectional traceability between docs and code.

## Success Criteria

### Extended Reference Format

- `SymbolicReference.ref` accepts project-qualified paths: `org/repo::path#symbol`
- The `::` delimiter separates the project qualifier from the file path
- Valid examples:
  - `acme/project-a::src/foo.py#FooClass` (class in project-a)
  - `acme/project-b::src/bar.py#BarClass::method` (method in project-b)
  - `acme/shared-lib::lib/utils.py` (entire module in shared-lib)
- Non-qualified paths remain valid for single-project (local) use:
  - `src/foo.py#FooClass` (local reference, no project qualifier)

### Validation Rules

- Project qualifier must be valid `org/repo` format (validated via existing `_require_valid_repo_ref`)
- File path after `::` follows existing validation rules
- Symbol path after `#` follows existing validation rules
- At most one `::` allowed (project delimiter)
- At most one `#` allowed (symbol delimiter)
- Order must be: `[org/repo::]file_path[#symbol_path]`

### Parsing Support

- Extend `parse_reference` in `symbols.py` to handle project qualification:
  - Add optional `current_project: str | None` parameter
  - Return `(project, file_path, symbol_path)` tuple (breaking change from current 2-tuple)
  - When reference has no `::` qualifier, use `current_project` as the project
  - When `current_project` is None and no qualifier present, project is None (local context)
- Update all call sites of `parse_reference` to handle the new return type
- The `is_parent_of` function should also accept `current_project` and use fully-qualified references for comparison

### Overlap Detection

- By inferring the current project, all parsed references become fully qualified
- Overlap detection compares fully-qualified references: same project + hierarchical containment
- `acme/proj::src/foo.py#Bar` and `src/foo.py#Bar` (with `current_project="acme/proj"`) correctly detect as overlapping
- References from different projects never overlap, even with identical file paths and symbols

### Test Coverage

- Unit tests for valid project-qualified references
- Unit tests for invalid formats (multiple `::`, wrong order, etc.)
- Tests for parsing with `current_project` inference
- Tests for overlap detection across project-qualified references
- Tests for backward compatibility with non-qualified (local) references

