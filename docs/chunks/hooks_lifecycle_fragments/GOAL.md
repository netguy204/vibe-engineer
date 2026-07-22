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
created_after: ["backend_live_validation"]
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

VE lifecycle commands carry a project-owned extension point. A repository
declares phase-scoped requirements by writing `docs/hooks/<command-name>.md`;
the wired lifecycle commands surface that file's body in their context block
via `` !`ve hooks show <command-name>` `` and treat it as binding operator
instruction for that phase.

The extension point exists because the lifecycle inflection points
(chunk-create, chunk-plan, chunk-implement, chunk-complete, ...) are the
natural place for repository-specific policy — "did this chunk change
public-facing documentation? If so, update it" — and that policy is only
relevant at its own inflection point. `CLAUDE.md` can express the same
sentence, but it is always-on: it pays context cost on every turn and
competes for attention with everything else in the preamble. A hook is
loaded precisely when it applies.

The event namespace is keyed on command name and is therefore flat across
artifact types: `docs/hooks/investigation-create.md` and
`docs/hooks/narrative-create.md` are as first-class as
`docs/hooks/chunk-complete.md`. Nothing in the mechanism is chunk-specific.
Chunks are merely where the lifecycle is densest, so they are where the
wired set starts.

`ve hooks` owns the resolution and rendering of these fragments so that
lifecycle commands — which ship as static plugin markdown in `commands/`,
not as rendered templates — need no per-event editing as the mechanism
grows. Adding an event is adding a file; adding a source (task workspace,
external artifact repo) is changing the CLI, not 37 command files.

The fragment format is parsed frontmatter plus a Markdown body. In this
chunk the frontmatter carries no required keys and the body is the whole
payload, but it is parsed rather than skipped so that a later enforced-check
key (`checks:`, shell commands that must pass) becomes an additive change to
an existing format rather than a migration of every operator's hook files.

Hooks are advisory: they are prompt content, and an agent can fail to honour
them. That limit is accepted here. Determinism is the job of the deferred
`checks:` key, not of this chunk.

## Success Criteria

- `ve hooks show <command-name>` prints the rendered fragment for
  `docs/hooks/<command-name>.md` relative to the project root, and prints
  nothing with exit 0 when the file is absent. Absent is the common case:
  every wired command runs this on every invocation in every project.
- The command never fails a lifecycle command it is embedded in. Malformed
  frontmatter, unreadable file, or absent `docs/hooks/` yields exit 0 and
  either empty output or a single diagnostic line — never a traceback and
  never a non-zero exit that would poison the calling command's context
  block.
- Rendered output identifies itself as project policy and names its source
  file, so the agent can distinguish operator-authored requirements from the
  command's own instructions and can cite the file when reporting.
- `ve hooks list` enumerates the fragments present in `docs/hooks/` and flags
  any whose filename matches no wired command. Silent no-op hooks are the
  primary failure mode of this design — an operator who writes
  `docs/hooks/chunk-completed.md` must find out from tooling, not from the
  hook never firing.
- `ve validate` reports an unrecognised `docs/hooks/` filename as a warning,
  for the same reason.
- The wired commands span artifact types, not just chunks: `chunk-create`,
  `chunk-plan`, `chunk-implement`, `chunk-complete`, `chunk-review`,
  `chunk-commit`, `investigation-create`, `narrative-create`, and
  `subsystem-discover`. Each gains one context line in its `## Context`
  section and one bullet in its `## Runtime context` section describing how
  to treat the content. Wiring only the chunk commands would make the
  mechanism read as chunk-only in practice regardless of what the namespace
  permits.
- The runtime-context bullet establishes precedence: hook content is a
  binding operator requirement for that phase and must be satisfied before
  the command reports completion; where a hook contradicts the command's own
  instructions, the agent surfaces the conflict to the operator rather than
  silently choosing a side.
- `docs/trunk/ARTIFACTS.md` documents hooks as an artifact type, and the
  `CLAUDE.md` template (`src/templates/claude/CLAUDE.md.jinja2`) mentions
  `docs/hooks/` so agents in a hook-using repository know the directory is
  meaningful. Regenerate with `ve init`.
- A project with no `docs/hooks/` directory behaves exactly as before.

## Implementation Notes

Context for the implementing agent, which will not have this conversation.

**Where the injection goes.** Lifecycle commands already open with a
`## Context` section of `` !`…` `` bash-substitution lines, followed by a
`## Runtime context` section that tells the agent how to interpret them.
See `commands/chunk-complete.md` lines 7-20 — it already does
`` !`cat .ve-config.yaml 2>/dev/null || echo "(no .ve-config.yaml — defaults
apply)"` ``. The hook line follows that established shape. Note that
`commands/*.md` are static, hand-maintained plugin files; they are *not*
rendered from `src/templates/`, despite the stale table in the root
`CLAUDE.md`.

**Where the CLI goes.** `ve hooks` is a new Click group registered in
`src/cli/__init__.py` alongside `chunk`, `friction`, `config`, etc. Follow
the existing pattern: a `src/cli/hooks.py` holding the group, with
resolution/rendering logic in a `src/hooks.py` business-logic module,
mirroring how `src/cli/friction.py` pairs with `src/friction.py`.

**Existing machinery to reuse.** `src/frontmatter.py` for parsing. Project
root discovery should match however sibling commands locate `docs/` (they
resolve from cwd).

**Naming collision, knowingly accepted.** `hooks/` at the repository root is
the Claude Code plugin hook directory (`hooks.json`, `session_start.sh`) — a
different, harness-level mechanism that fires on `SessionStart`, whose path
is fixed by Claude Code's auto-discovery convention and is not ours to
rename. VE hooks are unrelated to it. The operator weighed the collision and
accepted it rather than distort the name; do not "fix" it by renaming either
side. The collision is also confined to this source repository — consuming
projects have no root `hooks/`. Where prose could be read either way, say
"VE hook" or "plugin hook" rather than bare "hook".

**Scope boundaries.** Task workspaces (`.ve-task.yaml`) and external artifact
repos layer artifact locations; hook resolution in this chunk reads the
project root only. The CLI indirection exists so that layering can be added
later without touching command files, but adding it is not this chunk's work.

## Rejected Ideas

### Use `CLAUDE.md` for repository-specific lifecycle policy

The same instruction can be written into `CLAUDE.md` today, with no new
mechanism at all.

Rejected because: `CLAUDE.md` is always-on. Phase-specific policy loaded on
every turn pays context cost continuously and competes for attention against
the whole preamble, which is exactly the condition under which agents drop
instructions. Scoping the content to its inflection point is the feature.

### Store hook content inline in `.ve-config.yaml`

`.ve-config.yaml` already exists as project config and is already `cat`-ed
into lifecycle command context.

Rejected because: multi-paragraph prose inside YAML scalars is unpleasant to
author and produces poor diffs, and it conflates configuration values with
instruction content.

### Store hooks in `.ve/hooks/`

Rejected because: `.ve/` currently holds machine state (`orchestrator.db`,
`orchestrator.log`, chunk state). Putting operator-authored, reviewable
content there erodes the state/content boundary. `docs/hooks/` sits
alongside `docs/chunks/`, `docs/narratives/`, `docs/investigations/`, which
is what hooks are — operator intent, in git, under review.

### Name the mechanism `policies`, `rules`, or `checklists`

The injected header is itself prompt content, so a word carrying more
obligation ("Project policy:") applies more pressure than "Project hook:" —
which matters when v1 compliance is entirely voluntary. `rules` gives
similar force with less bureaucratic baggage; `checklists` is the most
literal description of what a v1 fragment is.

Rejected because: `policy` and `rules` over-promise deterministic
enforcement to the operator that VE cannot deliver until `checks:` exists,
and `checklists` ages badly against that same future key. `hooks` is the
term operators will guess first when asking "can I customise this lifecycle
step?", and it is neutral on enforcement, so it survives the advisory →
enforced transition unchanged.

### Prefix the name — `ve-hooks` or `chunk-hooks`

Explicit qualification would remove any chance of confusion with the Claude
Code plugin hook directory.

Rejected because: `chunk-hooks` would wrongly imply the mechanism is
chunk-specific, foreclosing hooks on investigations, narratives, and
subsystems — which the event namespace supports today. `ve-` is redundant
inside `docs/`, which is already VE's namespace (`docs/chunks/`, not
`docs/ve-chunks/`), and `ve ve-hooks show` stutters badly enough that the
CLI would remain `ve hooks` regardless — leaving the prefix on the directory
name alone, the one place the path is already unambiguous.

### Ship enforced shell checks in this chunk

A `checks:` key running shell commands that must exit 0 would make hooks
unignorable.

Rejected because: it requires deciding what failure means at each phase and
where the gate lives, and no `ve chunk complete` state-transition command
exists to gate on today — completion is agent-driven. Deferred deliberately;
the parsed-frontmatter format exists so it lands additively.

### Semantic events (`chunk.status_changed`) instead of command names

Decoupling event names from command names would survive command renames.

Rejected because: it adds an indirection layer and a naming vocabulary to
learn, for a problem (command renames) that has not occurred. Command names
are what the operator already knows.

### Separate `.pre` / `.post` fragments per command

`chunk-complete.post.md` would let the operator say "before you report done"
rather than "at command start" — which is arguably where the motivating
docs-sync example belongs.

Rejected because: it doubles the surface area before the single-fragment form
has been used. A fragment injected at command start can still say "before
reporting completion, ..." — the agent reads the whole command before acting.
If that proves insufficient in practice, `.pre`/`.post` is an additive
extension of the same filename convention.
