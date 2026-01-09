---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/models.py
  - src/subsystems.py
  - src/ve.py
  - tests/test_subsystem_status.py
code_references:
  - ref: src/models.py#VALID_STATUS_TRANSITIONS
    implements: "State machine rules defining valid status transitions"
  - ref: src/subsystems.py#Subsystems::get_status
    implements: "Get current status of a subsystem (SC 4)"
  - ref: src/subsystems.py#Subsystems::update_status
    implements: "Validate transition and update status (SC 1, 3)"
  - ref: src/subsystems.py#Subsystems::_update_overview_frontmatter
    implements: "Frontmatter update preserving other fields (SC 7)"
  - ref: src/ve.py#status
    implements: "CLI command with ID resolution and error handling (SC 2, 5, 6)"
  - ref: tests/test_subsystem_status.py
    implements: "Comprehensive test coverage for all success criteria"
narrative: 0002-subsystem_documentation
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
-->

# Chunk Goal

## Minor Goal

This chunk implements the `ve subsystem status` command for managing subsystem lifecycle transitions, enabling operators to signal consolidation intent through explicit status changes.

**Context**: Subsystem statuses communicate intent to agents:
- `DISCOVERING` → actively exploring the pattern
- `DOCUMENTED` → inconsistencies known, consciously deferred
- `REFACTORING` → actively consolidating, agents MAY expand scope
- `STABLE` → authoritative, agents should follow patterns
- `DEPRECATED` → being phased out, agents should avoid

The transition between statuses is not arbitrary—certain transitions require prior states to ensure subsystem documentation matures through a deliberate lifecycle.

**This chunk builds upon**:
- Chunk 0014-subsystem_schemas_and_model: Provides the `SubsystemStatus` enum
- Chunk 0016-subsystem_cli_scaffolding: Provides `ve subsystem` command group and `Subsystems` utility class

**Why now**: With the directory structure, CLI scaffolding, template, and bidirectional references in place, operators need a way to advance subsystems through their lifecycle. This command enforces valid transitions and updates the OVERVIEW.md frontmatter.

## Success Criteria

1. **Command implementation**: `ve subsystem status <id> <new-status>` updates the subsystem's OVERVIEW.md frontmatter status field

2. **ID resolution**: The command accepts either:
   - Full subsystem directory name: `0001-validation`
   - Just the shortname: `validation`

   If shortname is provided, it resolves to the full directory name using `Subsystems.find_by_shortname()`

3. **Transition validation**: The command enforces valid transitions per this state machine:
   ```
   DISCOVERING → DOCUMENTED | DEPRECATED
   DOCUMENTED  → REFACTORING | DEPRECATED
   REFACTORING → STABLE | DOCUMENTED | DEPRECATED
   STABLE      → DEPRECATED | REFACTORING
   DEPRECATED  → (terminal, no transitions out)
   ```
   Invalid transitions produce an error message explaining the current status and valid next states.

4. **Status display**: When called with just an ID (no new-status), the command displays the current status:
   ```
   $ ve subsystem status validation
   validation: DISCOVERING
   ```

5. **Error handling**:
   - Subsystem not found: "Subsystem 'foo' not found in docs/subsystems/"
   - Invalid status value: "Invalid status 'FOO'. Valid statuses: DISCOVERING, DOCUMENTED, REFACTORING, STABLE, DEPRECATED"
   - Invalid transition: "Cannot transition from DISCOVERING to STABLE. Valid transitions: DOCUMENTED, DEPRECATED"

6. **Output on success**: Prints the transition for confirmation:
   ```
   $ ve subsystem status validation DOCUMENTED
   validation: DISCOVERING → DOCUMENTED
   ```

7. **Frontmatter update**: The status field in the subsystem's OVERVIEW.md is updated in place, preserving all other frontmatter fields and document content

## Relationship to Parent

N/A - this is new functionality.
