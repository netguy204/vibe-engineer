---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
  - src/ve.py
  - src/task_utils.py
  - tests/test_task_chunk_list.py
code_references: []
narrative: 0001-cross_repo_chunks
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
-->

# Chunk Goal

## Minor Goal

Extend `ve chunk list` to detect task directory context and list chunks from the external chunk repository. This is the fifth chunk in the cross-repo narrative, building on the infrastructure from chunks 7-10.

When working in a task directory (detected by `.ve-task.yaml`), the current `ve chunk list` behavior doesn't make sense - there's no `docs/chunks/` in the task directory itself. Instead, the command should operate on the external chunk repository, showing all chunks with their dependent repos.

This directly advances docs/trunk/GOAL.md's required property: "It must be possible to perform the workflow outside the context of a Git repository."

## Success Criteria

### 1. Task Directory Detection

When `ve chunk list` runs:
- If in a task directory (`.ve-task.yaml` exists), operate in task-aware mode
- Otherwise, use existing single-repo behavior unchanged

### 2. Task-Aware List Output

When in a task directory, `ve chunk list` should:
- List chunks from the **external chunk repository** (not the task directory or projects)
- For each chunk, show the `dependents` repos from the chunk's GOAL.md frontmatter
- Output format shows the chunk and its dependent projects

Example output when run from a task directory:
```
docs/chunks/0002-auth_validation [IMPLEMENTING]
  dependents: acme/service-a (0005), acme/service-b (0009)
docs/chunks/0001-auth_token [ACTIVE]
  dependents: acme/service-a (0003), acme/service-b (0007)
```

### 3. Task-Aware --latest Flag

When `--latest` is used in a task directory:
- Return the highest IMPLEMENTING chunk from the **external chunk repository**
- Output format: `docs/chunks/{chunk_name}`

This allows commands like `$(ve chunk list --latest)` to work correctly in task context.

### 4. Preserved Single-Repo Behavior

When not in a task directory (using `--project-dir` or current directory):
- Behavior is identical to current implementation
- No dependents are shown (single-repo chunks don't have them)

### 5. Error Handling

- If in task directory but external repo not accessible: clear error message
- If external repo has no chunks: "No chunks found" error (same as current)
- If `--latest` but no IMPLEMENTING chunk in external repo: "No implementing chunk found" error

### 6. Tests

- Task-aware list shows external repo chunks with dependents
- Task-aware `--latest` returns external repo's implementing chunk
- Single-repo behavior unchanged (existing tests pass)
- Error cases: missing external repo, no chunks, no implementing chunk