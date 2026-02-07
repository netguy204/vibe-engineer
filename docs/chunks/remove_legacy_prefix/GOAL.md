---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
  - src/models.py
  - src/chunks.py
  - src/subsystems.py
  - src/narratives.py
  - src/investigations.py
  - src/cluster_rename.py
  - src/cli/chunk.py
  - src/cli/investigation.py
  - docs/trunk/SPEC.md
code_references: []
narrative: arch_decompose
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- chunks_decompose
- orch_worktree_cleanup
- validation_error_surface
- validation_length_msg
- orch_ready_critical_path
- orch_pre_review_rebase
- orch_merge_before_delete
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

FUTURE CHUNK APPROVAL REQUIREMENT:
ALL FUTURE chunks require operator approval before committing or injecting.
After refining this GOAL.md, you MUST present it to the operator and wait for
explicit approval. Do NOT commit or inject until the operator approves.
This applies whether triggered by "in the background", "create a future chunk",
or any other mechanism that creates a FUTURE chunk.

COMMIT BOTH FILES: When committing a FUTURE chunk after approval, add the entire
chunk directory (both GOAL.md and PLAN.md) to the commit, not just GOAL.md. The
`ve chunk create` command creates both files, and leaving PLAN.md untracked will
cause merge conflicts when the orchestrator creates a worktree for the PLAN phase.

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
- If this is the final chunk of a narrative, the narrative status should be set to COMPLETED
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

FRICTION_ENTRIES:
- Optional list of friction entries that this chunk addresses
- Provides "why did we do this work?" traceability from implementation back to accumulated pain points
- Format: entry_id is the friction entry ID (e.g., "F001"), scope is "full" or "partial"
  - "full": This chunk fully resolves the friction entry
  - "partial": This chunk partially addresses the friction entry
- When to populate: During /chunk-create if this chunk addresses known friction from FRICTION.md
- Example:
  friction_entries:
    - entry_id: F001
      scope: full
    - entry_id: F003
      scope: partial
- Validated by `ve chunk validate` to ensure referenced friction entries exist in FRICTION.md
- When a chunk addresses friction entries and is completed, those entries are considered RESOLVED

BUG_TYPE:
- Optional field for bug fix chunks that guides agent behavior at completion
- Values: semantic | implementation | null (for non-bug chunks)
  - "semantic": The bug revealed new understanding of intended behavior
    - Code backreferences REQUIRED (the fix adds to code understanding)
    - On completion, search for other chunks that may need updating
    - Status → ACTIVE (the chunk asserts ongoing understanding)
  - "implementation": The bug corrected known-wrong code
    - Code backreferences MAY BE SKIPPED (they don't add semantic value)
    - Focus purely on the fix
    - Status → HISTORICAL (point-in-time correction, not an ongoing anchor)
- Leave null for feature chunks and other non-bug work

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

DEPENDS_ON:
- Declares explicit implementation dependencies that affect orchestrator scheduling
- Format: list of chunk directory name strings, or null
- Default: [] (empty list - explicitly no dependencies)

VALUE SEMANTICS (how the orchestrator interprets this field):

| Value             | Meaning                              | Oracle behavior   |
|-------------------|--------------------------------------|-------------------|
| `null` or omitted | "I don't know my dependencies"       | Consult oracle    |
| `[]` (empty list) | "I explicitly have no dependencies"  | Bypass oracle     |
| `["chunk_a"]`     | "I depend on these specific chunks"  | Bypass oracle     |

CRITICAL: The default `[]` means "I have analyzed this chunk and it has no dependencies."
This is an explicit assertion, not a placeholder. If you haven't analyzed dependencies yet,
change the value to `null` (or remove the field entirely) to trigger oracle consultation.

WHEN TO USE EACH VALUE:
- Use `[]` when you have analyzed the chunk and determined it has no implementation dependencies
  on other chunks in the same batch. This tells the orchestrator to skip conflict detection.
- Use `null` when you haven't analyzed dependencies yet and want the orchestrator's conflict
  oracle to determine if this chunk conflicts with others.
- Use `["chunk_a", "chunk_b"]` when you know specific chunks must complete before this one.

WHY THIS MATTERS:
The orchestrator's conflict oracle adds latency and cost to detect potential conflicts.
When you declare `[]`, you're asserting independence and enabling the orchestrator to
schedule immediately. When you declare `null`, you're requesting conflict analysis.

PURPOSE AND BEHAVIOR:
- When a list is provided (empty or not), the orchestrator uses it directly for scheduling
- When null, the orchestrator consults its conflict oracle to detect dependencies heuristically
- Dependencies express order within a single injection batch (intra-batch scheduling)
- The chunks listed in depends_on will be scheduled to complete before this chunk starts

CONTRAST WITH created_after:
- `created_after` tracks CAUSAL ORDERING (what work existed when this chunk was created)
- `depends_on` tracks IMPLEMENTATION DEPENDENCIES (what must complete before this chunk runs)
- `created_after` is auto-populated at creation time and should NOT be modified manually
- `depends_on` is agent-populated based on design requirements and may be edited

WHEN TO DECLARE EXPLICIT DEPENDENCIES:
- When you know chunk B requires chunk A's implementation to exist before B can work
- When the conflict oracle would otherwise miss a subtle dependency
- When you want to enforce a specific execution order within a batch injection
- When a narrative or investigation explicitly defines chunk sequencing

EXAMPLE:
  # Chunk has no dependencies (explicit assertion - bypasses oracle)
  depends_on: []

  # Chunk dependencies unknown (triggers oracle consultation)
  depends_on: null

  # Chunk B depends on chunk A completing first
  depends_on: ["auth_api"]

  # Chunk C depends on both A and B completing first
  depends_on: ["auth_api", "auth_client"]

VALIDATION:
- `null` is valid and triggers oracle consultation
- `[]` is valid and means "explicitly no dependencies" (bypasses oracle)
- Referenced chunks should exist in docs/chunks/ (warning if not found)
- Circular dependencies will be detected at injection time
- Dependencies on ACTIVE chunks are allowed (they've already completed)
-->

# Chunk Goal

## Minor Goal

Remove all legacy `{NNNN}-{short_name}` prefix directory format support from the codebase. The only directory format going forward is `{short_name}`. There is no usage of the legacy format in the wild -- all artifact directories already use the new format.

This chunk eliminates dual-format handling scattered across the artifact resolution, validation, naming, and rename logic. Specifically:

- **`src/models.py`**: Remove the legacy branch from `extract_short_name()` (the `re.match(r"^\d{4}-", ...)` conditional), simplify `ARTIFACT_ID_PATTERN` and `CHUNK_ID_PATTERN` to only accept `{short_name}` format, remove legacy format validation branches in `ChunkRelationship.validate_chunk_id()` and `SubsystemRelationship.validate_subsystem_id()`, and update docstrings/comments that reference the dual format.
- **`src/chunks.py`**: Remove the legacy prefix match strategy from `resolve_chunk_id()` (the `name.startswith(f"{chunk_id}-")` branch) and update `find_duplicates()` to no longer call `extract_short_name` (since directory names are now always the short name).
- **`src/subsystems.py`**: Simplify `SUBSYSTEM_DIR_PATTERN` to only match `{short_name}`, remove the legacy branch from `is_subsystem_dir()`, and simplify `find_by_shortname()` and `find_duplicates()`.
- **`src/narratives.py`**: Simplify `find_duplicates()` to compare directory names directly instead of calling `extract_short_name`.
- **`src/investigations.py`**: Simplify `find_duplicates()` to compare directory names directly instead of calling `extract_short_name`.
- **`src/cluster_rename.py`**: Remove legacy format handling from `find_chunks_by_prefix()`, `check_rename_collisions()`, `_compute_new_chunk_name()`, and all reference-finding functions that call `extract_short_name`. Remove the `re.match(r"^\d{4}-", ...)` sequence-number preservation logic.
- **`src/cli/chunk.py`**: Remove `extract_short_name` usage in the `status` command.
- **`src/cli/investigation.py`**: Remove `extract_short_name` usage in the `status` command.
- **`docs/trunk/SPEC.md`**: Update directory naming sections for chunks, subsystems, and investigations to document only the `{short_name}` format. Remove references to `{NNNN}-` prefixes and chunk IDs as 4-digit numbers.
- **Tests**: Update all tests that create directories with legacy `{NNNN}-` format names, validate legacy patterns, or test legacy prefix matching. This includes tests across `test_models.py`, `test_chunks.py`, `test_subsystems.py`, `test_cluster_rename.py`, `test_narratives.py`, `test_investigations.py`, and others.

This simplification reduces code complexity and eliminates a class of confusing edge cases where the same artifact could be referenced by either its full `NNNN-name` directory or just `name`, enabling the downstream `models_subpackage` chunk (which depends on this one) to work with cleaner, simpler ID patterns.

## Success Criteria

- `extract_short_name()` in `src/models.py` is either removed or becomes a trivial identity function (returns its argument unchanged). No `\d{4}-` regex remains in the function.
- `ARTIFACT_ID_PATTERN` and `CHUNK_ID_PATTERN` in `src/models.py` no longer accept the `\d{4}-.+` alternative. They match only the `{short_name}` format (`^[a-z][a-z0-9_-]*$`).
- `ChunkRelationship.validate_chunk_id()` and `SubsystemRelationship.validate_subsystem_id()` in `src/models.py` have no legacy format branches or error messages referencing `{NNNN}-{short_name}`.
- `resolve_chunk_id()` in `src/chunks.py` has no legacy prefix match strategy (no `name.startswith(f"{chunk_id}-")` branch).
- `SUBSYSTEM_DIR_PATTERN` in `src/subsystems.py` no longer includes the `\d{4}-.+` alternative.
- `is_subsystem_dir()` in `src/subsystems.py` has no `re.match(r"^\d{4}-", ...)` branch.
- `_compute_new_chunk_name()` and `check_rename_collisions()` in `src/cluster_rename.py` have no `re.match(r"^\d{4}-", ...)` sequence-number preservation logic.
- No `re.match(r"^\d{4}-", ...)` pattern exists anywhere in the `src/` directory.
- `docs/trunk/SPEC.md` directory naming sections (Chunk Directory Naming, Subsystem Directory Naming, Investigation Directory Naming) describe only the `{short_name}` format without any `{NNNN}-` references.
- All tests pass (`uv run pytest tests/`). Tests that previously created legacy-format directories are updated to use `{short_name}` format, and tests that specifically verified legacy format handling are either removed or converted to verify the new-only format.
- No comments or docstrings in `src/` reference "legacy" format or `{NNNN}-` as a supported directory pattern.

