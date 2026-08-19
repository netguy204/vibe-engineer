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
depends_on: []
created_after: ["hooks_lifecycle_fragments"]
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

`ve validate`'s code-backreference scanner recognises `# Chunk:`, `# Narrative:`,
and `# Subsystem:` comments only where they are genuine comments, not where the
same text appears inside a string literal. A Python file that writes a specimen
backreference into a fixture string, or embeds one in a docstring or prototype,
no longer produces a phantom "references non-existent chunk" error.

The scanner today is a `re.MULTILINE` regex (`CHUNK_BACKREF_PATTERN` et al. in
`src/backreferences.py`) applied line-by-line in
`src/integrity.py#IntegrityValidator::_validate_code_backreferences` and in
`src/backreferences.py#count_backreferences` / `update_backreferences`. Because
`^` under `re.MULTILINE` matches the start of any line, a `# Chunk: ...` line
sitting inside a triple-quoted string matches exactly as if it were a real
comment. The scanner has no awareness of the host language's syntax.

**Scope note — what the scanner does and does not see.** The pattern is
`^#\s+`, which recognises exactly one form: a `#` at column zero. It does not
recognise indented `#` comments, and it does not recognise any other language's
comment syntax (`//`, `%`, `;`, `--`) even though `enumerate_source_files`
enumerates those files. Those are false *negatives* — real backreferences the
scanner silently drops — and they are the subject of a separate chunk,
`backref_comment_forms`. This chunk is only about the false *positives*: text
that is not a comment being read as one. Do not widen the pattern here; the two
chunks edit the same constants and the same three call sites, and
`backref_comment_forms` declares `depends_on: ["validate_backref_literals"]` to
run after this one.

The result is that `ve validate` fails out of the box on this very repository
with ~50 errors, none of which are real broken references:

- 17 in `tests/test_narrative_consolidation.py`, whose fixtures write fake
  `# Chunk: docs/chunks/chunk_one` lines into temp files as test *input* for the
  backreference machinery it exercises.
- 32 across `docs/investigations/chunk_reference_decay/prototypes/*.py`, which
  carry specimen backref strings.
- 1 in `docs/chunks/causal_ordering_migration/migrate.py`, a stale reference in
  an archived one-off migration script (a genuinely dangling reference, not a
  false positive — see Success Criteria).

A validator that reports 50 errors on a clean checkout trains its users to
ignore it, which is corrosive for a tool whose entire purpose is referential
integrity — and it forecloses using `ve validate` as a completion gate.

## Success Criteria

- On a clean checkout of this repository, `ve validate` reports zero *false*
  code-backreference errors: the 49 arising from `# Chunk:`/`# Subsystem:` text
  inside Python string literals and docstrings are gone.
- Backreferences that are real comments continue to be validated exactly as
  before. A genuinely dangling backreference comment (e.g. `# Chunk:
  docs/chunks/deleted_thing`) is still reported. Regression coverage must
  include both a real dangling comment (still an error) and a string-literal
  specimen (no longer an error) in the same file.
- The genuinely stale reference in
  `docs/chunks/causal_ordering_migration/migrate.py` is resolved on its own
  terms — either the reference is corrected/removed, or that migration artifact
  is confirmed archival and excluded — rather than being masked by the
  string-literal fix. Decide which after inspecting it; do not assume.
- The three code paths that scan for backreferences stay consistent:
  `_validate_code_backreferences` (validation),
  `backreferences.count_backreferences` (statistics), and
  `backreferences.update_backreferences` (reference rewriting during
  chunk-complete). If the scanner learns to skip string literals, the rewriter
  must skip them too, or it will corrupt fixture strings when it updates
  references. This is the subtle risk: the fix is not only in the validator.
- `ve validate` exits 0 on this repository once the fix and the one stale
  reference are addressed (independent of the pre-existing `hook→command`
  warnings, which are warnings, not errors).

## Implementation Notes

Context for the implementing agent.

**Root cause.** `src/backreferences.py` lines ~40-42:
`re.compile(r"^#\s+Chunk:\s+docs/chunks/([a-z0-9_-]+)", re.MULTILINE)`. Applied
per-line, `^` matches inside string literals. Python is the only language
producing false positives in this repo, and Python has `tokenize`/`ast` in the
stdlib, so the Python path can be made syntax-aware cheaply: tokenize the file,
consider only `COMMENT` tokens, and match the pattern against those. The
`enumerate_source_files` set spans multiple languages
(`src/source_files.py`), so a fully language-agnostic string-literal skip is
harder; scope this chunk to the Python case, which is where every real false
positive lives, and leave non-Python files on the existing line-based path.

Note that tokenizing incidentally makes indented Python `# Chunk:` comments
match, since a `COMMENT` token carries no leading whitespace — 477 occurrences
in this repository that the `^#` anchor currently misses. That is a side effect,
not this chunk's intent, but it is a welcome one and should not be suppressed.
Whatever remains of the indentation gap belongs to `backref_comment_forms`.

**Do not** solve this by editing the fixtures to dodge the pattern. That would
green the build while leaving the scanner able to false-positive on any future
file. The scanner is the defect.

**Three call sites, one behaviour.** Whatever "is this a real comment" logic is
introduced must be shared by the validator and the rewriter
(`update_backreferences`), not duplicated or applied to only one. The rewriter
mutating a `# Chunk:` inside a fixture string during chunk-complete would be a
worse bug than the false positive.

**Relationship to hooks_lifecycle_fragments.** Discovered while reviewing that
chunk, where `ve validate` could not serve as a completion gate because of this
noise. Unrelated in substance — that chunk added a `hook→command` warning; this
is a pre-existing scanner defect on a different code path.

## Rejected Ideas

### Break the pattern in the offending fixture/prototype files

Rewrite the test fixtures so `# Chunk:` no longer starts a line (e.g. string
concatenation, or a leading space).

Rejected because: it hides the symptom and leaves the scanner able to
false-positive on the next file anyone writes containing specimen backref text.
The scanner's inability to distinguish comments from string contents is the bug.
