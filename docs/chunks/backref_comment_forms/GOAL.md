---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: ["validate_backref_literals"]
created_after: ["external_never_resolved", "hooks_lifecycle_fragments", "claudemd_marker_safety", "claudemd_symlink_notice", "template_workspace_awareness"]
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

VE's backreference scanner recognises a backreference comment in any language
`enumerate_source_files` enumerates, written in that language's comment syntax,
at any indentation. A `// Chunk: docs/chunks/foo` on an indented method in
TypeScript is seen by `ve validate`, counted by `ve stats`, and rewritten by
`ve chunk complete` exactly as a column-zero `# Chunk:` in Python is.

The scanner currently recognises exactly one form: `#`, at column zero,
followed by whitespace. `CHUNK_BACKREF_PATTERN` and `SUBSYSTEM_BACKREF_PATTERN`
in `src/backreferences.py` are anchored `^#\s+`, and all three consumers apply
them per-line — `IntegrityValidator::_validate_code_backreferences`
(`src/integrity.py`, via `.match(line)`), `backreferences.count_backreferences`
(via `findall` under `re.MULTILINE`), and `backreferences.update_backreferences`
(via `.match(line)`). Two whole classes of backreference are therefore
invisible to every one of them:

- **Non-`#` comment syntaxes.** `SOURCE_EXTENSIONS` in `src/source_files.py`
  enumerates ~40 extensions across ~20 languages, most of which comment with
  `//` (JS/TS, Go, Rust, Java, Kotlin, Swift, C/C++, C#, PHP, Scala) and a few
  with `%` (Erlang), `;` (Clojure), or `--` (Lua). Their files are opened and
  scanned; none of their comments can ever match. In this repository that is
  102 `// Chunk:`/`// Subsystem:` backreferences across 18 files in
  `workers/leader-board/` and `site/`.
- **Indented comments.** `^#` requires column zero, so any class- or
  method-level backreference is missed even in Python. That is 477 occurrences
  across 102 Python files in `src/` and `tests/` — and 69 of the 102 `//`
  backreferences above, which would still be missed if the prefix were fixed
  and the anchor were not.

Both gaps are silent. Nothing reports a backreference it could not parse, so
the failure presents as absence: `ve validate` passes, `ve stats` undercounts,
and — worst — `ve chunk complete` renames the references it can see and leaves
the rest dangling with no error. The tool's own PLAN template instructs agents
to place backreferences at class and method level, and several chunk PLANs in
this repository (`gateway_cleartext_api`, `invite_list_revoke`,
`websocket_zombie_cleanup`) instruct agents to write `// Chunk:` comments into
TypeScript. VE asks for backreferences in forms it cannot read.

## Success Criteria

- A backreference written in the host language's line-comment syntax is
  recognised for every language in `SOURCE_EXTENSIONS`. At minimum `//`, `#`,
  `%`, `;`, and `--` are supported, mapped by file extension rather than
  probed for — a `#` inside a `.ts` file is not a comment and must not match.
- Leading whitespace before the comment marker is accepted. The 477 indented
  Python backreferences and the 69 indented `//` backreferences in this
  repository are counted by `ve stats`.
- All three consumers share the change. `_validate_code_backreferences`,
  `count_backreferences`, and `update_backreferences` must agree on what a
  backreference is; a scanner that sees more than the rewriter rewrites is
  worse than today's, because `ve chunk complete` would then report success
  while leaving newly-visible references stale.
- `update_backreferences` preserves the original indentation and comment
  marker when it rewrites a line. Rewriting `    // Chunk: docs/chunks/old`
  must yield `    // Chunk: docs/chunks/new`, not a reindented or
  `#`-prefixed line.
- Newly-visible backreferences that point at nothing are reported as errors,
  not silently tolerated. Running `ve validate` on this repository after the
  change surfaces whatever dangling references the 579 previously-invisible
  backreferences contain; that count is expected to be non-zero and resolving
  those is part of this chunk.
- Regression coverage includes a `.ts` file with an indented `// Chunk:`
  backreference, a `.py` file with an indented `# Chunk:` backreference, and a
  negative case proving a `#`-prefixed line in a `//`-language file does not
  match.

## Relationship to validate_backref_literals

These two chunks edit the same three call sites and the same pattern
constants, so they must not run concurrently. `depends_on` names
`validate_backref_literals` to force the order.

`validate_backref_literals` makes the Python path syntax-aware by tokenizing
and matching only `COMMENT` tokens. That incidentally fixes the indented-`#`
case for Python, since a comment token carries no leading whitespace. This
chunk should therefore be re-scoped at planning time against whatever that
chunk actually landed: the non-`#` comment syntaxes are this chunk's core, and
the indentation fix applies to whichever files remain on the line-based path.

The two chunks are opposite failure modes of the same defect — the scanner has
no model of the host language. `validate_backref_literals` addresses the false
positives (backreference text inside Python string literals, reported as real).
This chunk addresses the false negatives (real comments the pattern cannot
express). If planning finds that a single language-aware comment extractor
subsumes both cleanly, say so rather than layering a second mechanism.

## Rejected Ideas

### Match any of `#`, `//`, `%`, `;`, `--` regardless of file type

A single alternation pattern applied to every file, ignoring extension.

Rejected because: it trades a false-negative bug for a false-positive one. `#`
begins a preprocessor directive in C and a shebang anywhere; `--` begins SQL
comments but also appears in TS as decrement; `;` is a statement terminator in
half the enumerated languages. The prefix set must be selected by extension.

### Emit a warning for unparseable backreference-looking lines

Detect `Chunk: docs/chunks/...` text in any form and warn when it is not in a
recognised comment position.

Rejected because: it reintroduces exactly the false-positive class that
`validate_backref_literals` exists to remove — prose in a docstring or a
specimen string would warn. Recognise the real forms; do not guess at the rest.
