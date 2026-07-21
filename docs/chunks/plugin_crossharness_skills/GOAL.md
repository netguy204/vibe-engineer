---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: ["watch_handshake_5xx_retry"]
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

The vibe-engineer plugin distributes the entire agent-facing workflow as
**cross-harness skills** — `skills/<name>/SKILL.md` (agentskills.io directory
layout) — rather than Claude Code commands (`commands/*.md`). The plugin's
`commands/` directory ships no workflow content; it is reserved for a future
in which some interaction is genuinely command-shaped (Claude-Code-specific
UX), but today the workflow is fully representable as skills.

**The guarded intent:** the vibe-engineer workflow is plausibly cross-harness.
Claude Code is the primary supported target, but the skill representation must
not *depend* on Claude-Code-only machinery. Concretely, each SKILL.md is
self-contained: context the agent needs (ve CLI availability, `.ve-task.yaml`
task-workspace detection, `.ve-config.yaml` project config) is gathered by
**instructing the agent to run commands**, not by Claude Code's `` !`...` ``
slash-command preprocessing, which other harnesses (and Claude Code's own
Skill-tool invocation path) do not execute.

This amends a DEC-010 consequence. DEC-010 (plugin-based distribution) stated:
"The agent-agnostic `.agents/skills/` (agentskills.io) layout is dropped;
non-Claude-Code agent support narrows to the AGENTS.md pointer file… if
multi-agent support becomes a requirement later, a render channel can be
reintroduced from the plugin sources." This chunk reintroduces the
cross-harness layout *as the plugin's native format* rather than as a render
channel — one source of truth, no drift.

## Context

- **Motivating failure (2026-07-21):** a Claude Code session invoked
  `Skill(vibe-engineer:chunk-create)` and got `Unknown skill` — the plugin's
  `skills/` directory contains only `.gitkeep` while all 38 workflow docs live
  in `commands/`. Plugin commands surface as slash commands but not as
  Skill-tool-invocable skills. The agent fell back to reading
  `commands/chunk-create.md` off disk, which silently skipped the `` !`...` ``
  dynamic context block (ve CLI check, task-workspace detection) — exactly the
  failure mode the self-containment constraint above prevents.
- **Current layout:** 38 files in `commands/` at the repo root (chunk-*,
  narrative-*, orchestrator-*, steward-*, swarm-*, entity-*, plus
  audit-intent, cluster-rename, decision-create, discover-subsystems,
  friction-log, investigation-create, migrate-managed-claude-md,
  subsystem-discover, validate-fix, ve-status). `skills/` is empty.
  `agents/` (subagents) and `hooks/` (session_start) are **out of scope** —
  unchanged.
- **Frontmatter:** command files carry `name`, `description`, and some carry
  `allowed-tools` (e.g. `commands/chunk-create.md`). Skills keep `name` +
  `description` (required by both Claude Code and agentskills.io);
  `allowed-tools` may be retained where present — harnesses that don't
  understand it ignore extra frontmatter keys.
- **Dynamic context blocks:** `plugin_runtime_context` introduced `## Context`
  sections using `` !`ve --help …` ``-style substitution in several commands
  (at minimum `chunk-create`). These must be converted to explicit "gather
  context first" instructions (the pre-plugin `.agents/skills/` renders, e.g.
  the legacy `.agents/skills/chunk-create/SKILL.md` "## Tips" section, show
  the instruction-driven style). Audit all 38 files for `` !` `` usage.
- **Naming:** skill directory names mirror the command basenames
  (`commands/chunk-create.md` → `skills/chunk-create/SKILL.md`), matching the
  naming the legacy `.agents/skills/` structure used.
- **Related chunks:** `plugin_scaffold` (plugin/marketplace layout),
  `plugin_core_commands` / `plugin_orch_commands` (the static ports being
  moved — their `code_paths`/`code_references` point at `commands/*.md` and
  will need updating via `/chunks-resolve-references` or at completion),
  `plugin_runtime_context` (the context-detection pattern being preserved in
  instruction form), `agentskills_migration` (the original cross-harness
  layout this restores at the plugin level).
- **Decision record:** update DEC-010's consequence in
  `docs/trunk/DECISIONS.md` (or add a new decision via `/decision-create`)
  recording that the plugin ships cross-harness skills and why.

## Success Criteria

- Every workflow doc previously at `commands/<name>.md` ships at
  `skills/<name>/SKILL.md`; `commands/` contains no workflow content.
- Each SKILL.md has valid `name` + `description` frontmatter and is
  self-contained: no `` !`...` `` preprocessing or other Claude-Code-only
  machinery required for correct execution; runtime context detection is
  expressed as explicit instructions to run commands.
- In a fresh Claude Code session with the plugin installed,
  `Skill(vibe-engineer:chunk-create)` resolves (the motivating bug is fixed),
  and skills are invocable as `/chunk-create`-style slash invocations.
- DEC-010's consequence is amended (or a new decision added) documenting the
  cross-harness-skills distribution and the "commands reserved for genuinely
  command-shaped future UX" boundary.
- `code_references` in the affected `plugin_*` chunks that point at
  `commands/*.md` are updated to the new `skills/` paths.
- Existing tests pass (`uv run pytest tests/`), including the
  plugin/CLI co-versioning check in `tests/test_session_hook.py`; any test
  referencing `commands/` paths is updated.

## Rejected Ideas

### Ship both commands/ and skills/ (dual surface)

Keep `commands/*.md` and add `skills/` mirroring them, so slash commands and
Skill-tool invocation both work from their "native" directories.

Rejected because: two copies of every workflow doc is exactly the
two-sources-of-truth drift DEC-010 rejected when it killed the render
channel. Skills already surface as slash invocations; the dual layout buys
nothing.

### Keep commands/ as the format and register them as skills some other way

Rejected because: the operator's intent is that the workflow is
**cross-harness** — the agentskills.io `skills/<name>/SKILL.md` layout is the
portable representation. `commands/` remains available for a future in which
something is genuinely Claude-Code-command-shaped, but nothing today is.