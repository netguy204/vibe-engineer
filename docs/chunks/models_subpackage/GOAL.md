---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
  - src/models/__init__.py
  - src/models/shared.py
  - src/models/references.py
  - src/models/subsystem.py
  - src/models/investigation.py
  - src/models/narrative.py
  - src/models/friction.py
  - src/models/reviewer.py
  - src/models/chunk.py
code_references: []
narrative: arch_decompose
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- remove_legacy_prefix
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

Split `src/models.py` (834 lines) into a `src/models/` subpackage with domain-specific modules, each holding the Pydantic models, enums, constants, and validators for a single artifact domain. After `remove_legacy_prefix` has eliminated the dual-format directory handling, the remaining code groups cleanly by domain with minimal cross-cutting concerns.

The target module layout:

- **`models/__init__.py`** -- Re-exports every public name so that all existing `from models import X` statements continue to work with zero consumer changes.
- **`models/chunk.py`** -- `ChunkStatus`, `BugType`, `VALID_CHUNK_TRANSITIONS`, `ChunkFrontmatter`, `ChunkDependent`. Everything governing the chunk lifecycle and its GOAL.md frontmatter.
- **`models/subsystem.py`** -- `SubsystemStatus`, `VALID_STATUS_TRANSITIONS`, `ComplianceLevel`, `ChunkRelationship`, `SubsystemFrontmatter`. The subsystem documentation lifecycle and chunk-to-subsystem relationships.
- **`models/narrative.py`** -- `NarrativeStatus`, `VALID_NARRATIVE_TRANSITIONS`, `NarrativeFrontmatter`. The narrative lifecycle.
- **`models/investigation.py`** -- `InvestigationStatus`, `VALID_INVESTIGATION_TRANSITIONS`, `InvestigationFrontmatter`. The investigation lifecycle.
- **`models/references.py`** -- `ArtifactType`, `ARTIFACT_ID_PATTERN`, `CHUNK_ID_PATTERN`, `SymbolicReference`, `CodeRange`, `CodeReference`, `ExternalArtifactRef`, `SubsystemRelationship`, `ProposedChunk`. Shared reference types used across multiple artifact frontmatter schemas.
- **`models/friction.py`** -- `FrictionTheme`, `FrictionProposedChunk`, `FrictionFrontmatter`, `FrictionEntryReference`, `ExternalFrictionSource`, `FRICTION_ENTRY_ID_PATTERN`, `FrictionFrontmatter`. The friction log domain.
- **`models/reviewer.py`** -- `TrustLevel`, `LoopDetectionConfig`, `ReviewerStats`, `ReviewerMetadata`, `ReviewerDecision`, `FeedbackReview`, `DecisionFrontmatter`. The reviewer agent domain.
- **`models/shared.py`** -- `extract_short_name`, `_require_valid_dir_name`, `_require_valid_repo_ref`, `SHA_PATTERN`, `TaskConfig`. Utility functions and cross-cutting helpers used by multiple domain modules.

This decomposition makes each domain independently navigable for both agents and humans, reduces the cost of understanding any single domain, and enables downstream chunks (`chunk_validator_extract`, `project_artifact_registry`) to import from clean, focused locations.

## Success Criteria

- **Backward-compatible imports**: Every existing `from models import X` statement across the codebase (chunks.py, subsystems.py, narratives.py, investigations.py, friction.py, reviewers.py, external_refs.py, external_resolve.py, integrity.py, artifact_ordering.py, task_utils.py, cluster_rename.py, state_machine.py, consolidation.py, cluster_analysis.py, cli/chunk.py, cli/narrative.py, cli/subsystem.py, cli/investigation.py, cli/external.py, cli/orch.py, cli/reviewer.py, orchestrator/scheduler.py) continues to resolve correctly via `models/__init__.py` re-exports.
- **No behavioral changes**: All existing tests pass (`uv run pytest tests/`) with no modifications to test assertions. The models, validators, and enums behave identically.
- **Single-responsibility modules**: Each new module under `models/` contains only the types, enums, constants, and validators for one artifact domain. No module exceeds ~200 lines.
- **`src/models.py` is replaced**: The monolithic file is deleted and replaced by the `src/models/` package directory. No stale `models.py` coexists with the package.
- **Clean internal imports**: Domain modules import shared utilities from `models.shared` rather than duplicating code. Cross-domain references (e.g., `ChunkFrontmatter` referencing `SubsystemRelationship` and `FrictionEntryReference`) use explicit intra-package imports.
- **Re-export completeness**: `models/__init__.py` re-exports every public name that was previously available from the flat `models.py` module. Running `dir(models)` from a consumer yields the same public names.

