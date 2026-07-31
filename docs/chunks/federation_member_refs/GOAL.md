---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models/shared.py
- src/models/references.py
- src/backreferences.py
- src/workspace_validation.py
- src/integrity.py
- docs/trunk/SPEC.md
- tests/test_models.py
- tests/test_backreferences.py
- tests/test_workspace_validation.py
- tests/test_integrity.py
- tests/test_chunks.py
code_references:
- ref: src/models/shared.py#classify_qualifier_shape
  implements: The single qualifier shape rule shared by comments and frontmatter -
    no slash is a workspace member, one slash is org/repo, anything else is invalid
- ref: src/backreferences.py#_classify_qualifier
  implements: Comment-grammar classification delegating its shape rules to the shared
    function instead of mirroring them
- ref: src/models/references.py#SymbolicReference
  implements: Frontmatter refs accept member-qualified forms under the shared shape
    rule, rejecting invalid qualifiers with both accepted forms named
- ref: src/workspace_validation.py#_Validator::check_code_references
  implements: Member-qualified file parts resolve through the workspace manifest and
    are verified in the target tree - existence, glob expansion, and symbol anchors
    - while org/repo stays unverified and malformed qualifiers become defects
- ref: src/integrity.py#IntegrityValidator::_validate_chunk_file_paths
  implements: Single-tree deferral of qualified declared-path entries to workspace
    validation, so cross-tree refs are not misresolved locally
- ref: tests/test_workspace_validation.py#test_member_qualified_code_reference_is_verified_clean
  implements: The headline behavior - a resolving member ref appears in neither defects
    nor unverified
- ref: tests/test_models.py#TestSymbolicReferenceMemberQualifiers
  implements: Member-qualified frontmatter acceptance and comment/frontmatter shape-rule
    parity
- ref: tests/test_integrity.py#TestIntegrityValidatorFilePaths::test_qualified_entries_are_deferred_to_workspace_validation
  implements: Qualified entries produce no single-tree chunk-to-file errors
- ref: tests/test_chunks.py#TestParseChunkFrontmatterWithErrors::test_invalid_code_reference_format_returns_error
  implements: Invalid-ref fixtures use a multi-slash qualifier now that the member
    form is valid
narrative: reference_integrity
investigation: null
subsystems: []
friction_entries: []
depends_on:
- crossref_workspace_parity
- crossref_glob_refs
created_after:
- crossref_rename_integrity
- validation_backref_allowlist
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

STATUS VALUES (status answers: how much of the intent does this chunk own?):
- FUTURE: Not yet owned. Queued for later.
- IMPLEMENTING: Being taken into ownership. At most one per worktree.
- ACTIVE: Fully owns the intent that governs the code.
- COMPOSITE: Shares ownership with other chunks. Must be read alongside its co-owners.
- HISTORICAL: No longer owns intent. Kept for archaeological context.

See docs/trunk/CHUNKS.md for the full principle.

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
- Format: subsystem_id is the subsystem directory name, relationship is "implements" or "uses"
- "implements": This chunk directly implements part of the subsystem's functionality
- "uses": This chunk depends on or uses the subsystem's functionality
- Example:
  subsystems:
    - subsystem_id: "validation"
      relationship: implements
    - subsystem_id: "frontmatter"
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

CHUNK ARTIFACTS:
- Single-use scripts, migration tools, or one-time utilities created for this chunk
  should be stored in the chunk directory (e.g., docs/chunks/foo/migrate.py)
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

Add a verified member-qualified reference form for intra-workspace cross-tree references. Today workspace validation routes any ref whose file part contains '::' to unverified with reason 'cross-repository targets are not resolved offline' (src/workspace_validation.py ~line 810), so a path that genuinely lives in a sibling tree of the same working copy (e.g. a chunk's CI gate now in the root tree's .github/workflows/) can only be written in a form that silences the check while looking resolved. Design a member::path form that resolves through the workspace manifest and IS verified, kept distinct from repo-qualified org/repo refs which legitimately cannot be checked offline. Read docs/chunks/federation_qualified_refs and the federation cluster first; this chunk belongs to that initiative and must not fork its addressing semantics.

<!--
Write this as a present-tense architectural fact — the state of the system
once this chunk is ACTIVE and fully owns its intent. ("ACTIVE: Fully owns
the intent that governs the code.")

Ask yourself: "If this chunk has been merged and is governing its code for
the next three years, what is true about the architecture?"

PREFER state verbs: "emits", "enforces", "exposes", "tolerates", "owns",
"validates", "accepts", "rejects", "routes", "propagates"

AVOID action verbs: "add", "wire", "make", "implement", "migrate", "fix"

AVOID transitory framing: "accomplishes", "enables", "next step",
"completing this", "in order to"

Contrast:
  ❌ Transitory: "Wire progress() calls into the snapshot pipeline so the
     CLI can show completion estimates."
  ✅ Stative: "The snapshot pipeline emits progress() events at each
     natural unit-of-work boundary, enabling downstream consumers to
     report completion estimates."

Keep this focused on a single architectural state. If you find yourself
describing multiple independent states, split into separate chunks.
-->

## Success Criteria

- `SymbolicReference` accepts `member::path` and `member::path#symbol`
  frontmatter refs under the same shape rules the comment grammar's
  `_classify_qualifier` enforces (no `/`, identifier with dots, no length
  cap), and the two share one rule in code rather than two mirrors.
- `ve workspace validate` *verifies* a member-qualified `code_paths` or
  `code_references` entry against the named member's tree: existence, glob
  expansion, and symbol anchors all resolve through the workspace manifest,
  and a resolving member ref appears in neither `defects` nor `unverified`.
- Failure routing is honest and manifest-aware: an unknown member qualifier
  is an `UNKNOWN_QUALIFIER` defect with registration guidance; a missing
  target in a known member's tree is an `UNRESOLVABLE_FRONTMATTER` defect
  naming that tree; a malformed qualifier is a `MALFORMED_QUALIFIER` defect
  — none of them a fake "cross-repository" unverified.
- `org/repo::` refs keep their existing disposition: collected in
  `unverified` with the cross-repository reason, never defects.
- All new finding sites anchor lines via `_find_field_entry_line` on the
  owning field's entry.
- Single-tree validation (`IntegrityValidator._validate_chunk_file_paths`)
  defers qualified entries to workspace validation instead of checking them
  as literal local paths.
- SPEC.md's Code Reference Format documents both qualified forms and which
  validator verifies each.

## Rejected Ideas

### Require the member target to be a VE tree for file-part resolution

Backreference resolution (`check_member_reference`) requires the member root
to be a VE tree, because it addresses artifacts under `docs/`. Applying the
same gate to file parts was rejected: a plain file target does not live
under `docs/`, and `resolve_peer_pointer` already established that peer
resolution gates on manifest registration plus a filesystem read. Requiring
`is_member_tree` here would make a legitimate `root::.github/workflows/ci.yml`
reference fail for a reason unrelated to whether the file exists.