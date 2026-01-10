---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/chunks.py
  - src/ve.py
  - src/task_utils.py
  - src/templates/chunk/GOAL.md.jinja2
  - src/templates/commands/chunk-create.md
  - tests/test_chunks.py
  - tests/test_chunk_start.py
  - tests/test_chunk_list.py
  - tests/test_chunk_activate.py
  - tests/test_task_utils.py
code_references:
  - ref: src/chunks.py#Chunks::get_current_chunk
    implements: "Returns highest-numbered IMPLEMENTING chunk, ignoring FUTURE/ACTIVE/SUPERSEDED/HISTORICAL"
  - ref: src/chunks.py#Chunks::activate_chunk
    implements: "Transitions FUTURE chunk to IMPLEMENTING, enforcing single IMPLEMENTING constraint"
  - ref: src/chunks.py#Chunks::create_chunk
    implements: "Extended with status parameter to support FUTURE and IMPLEMENTING statuses"
  - ref: src/ve.py#start
    implements: "CLI command with --future flag for creating FUTURE chunks"
  - ref: src/ve.py#list_chunks
    implements: "CLI command showing status in brackets, --latest uses get_current_chunk"
  - ref: src/ve.py#activate
    implements: "CLI command to activate a FUTURE chunk to IMPLEMENTING"
  - ref: src/task_utils.py#update_frontmatter_field
    implements: "Reusable utility for modifying YAML frontmatter fields"
  - ref: src/task_utils.py#create_task_chunk
    implements: "Extended to pass status parameter for cross-repo chunk creation"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "Template with FUTURE status documentation and Jinja status variable"
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Skill checks for IMPLEMENTING chunk and defaults to --future"
  - ref: docs/trunk/SPEC.md
    implements: "Specification updated with FUTURE status, --future flag, and ve chunk activate"
narrative: null
created_after: ["0012-symbolic_code_refs"]
---

# Chunk Goal

## Minor Goal

Add the ability to create "future" chunks while a chunk is actively in progress. Currently, when working through a chunk, developers often recognize related work that should be captured for later execution. This feature enables capturing those future chunks without disrupting the current work.

This supports the vibe-engineer workflow (docs/trunk/GOAL.md) by allowing continuous capture of work items during implementation, preventing loss of context and ensuring related work is properly sequenced.

## Success Criteria

1. **New "FUTURE" status value**: Add `FUTURE` to the valid status values in the GOAL.md schema comment and in validation logic

2. **Modified `ve chunk start` behavior**: Accept an optional `--future` flag that creates the chunk with status `FUTURE` instead of `IMPLEMENTING`

3. **Updated `/chunk-create` skill**: The skill should intelligently decide whether to use `--future` based on the user's prompt:
   - If the prompt describes work to do "later", "next", "after this", or is being captured while another chunk is in progress, use `--future`
   - If the prompt describes immediate work or there's no current IMPLEMENTING chunk, create normally
   - The skill should check for an existing IMPLEMENTING chunk and factor that into the decision

4. **Updated "current chunk" resolution**: `get_latest_chunk()` (or a new `get_current_chunk()` method) should find the highest-numbered chunk with status `IMPLEMENTING` (not `FUTURE`, `ACTIVE`, `SUPERSEDED`, or `HISTORICAL`)

5. **New `ve chunk list` command**: List all chunks showing chunk number, short name, and status (simple format)

6. **Transition from FUTURE to IMPLEMENTING**: Add `ve chunk activate <chunk_id>` command that:
   - Fails with an error if another chunk is currently `IMPLEMENTING` (only one IMPLEMENTING chunk allowed at a time)
   - Changes the specified FUTURE chunk's status to `IMPLEMENTING`

7. **Tests**: All new behavior is covered by unit tests

## Design Notes

- **Single IMPLEMENTING constraint**: At most one chunk can have status `IMPLEMENTING` at any time. This ensures clear focus and prevents ambiguity about which chunk is "current."
- **Workflow**: Complete or mark the current chunk ACTIVE before activating a future chunk
- **Chunk numbering**: Future chunks still get sequential numbers when created, preserving chronological order of when work was identified
- **Skill intelligence**: The `/chunk-create` skill should be context-aware. When invoked while a chunk is already IMPLEMENTING, it should default to creating a FUTURE chunk unless the user explicitly indicates they want to switch focus. This prevents accidental creation of multiple IMPLEMENTING chunks.