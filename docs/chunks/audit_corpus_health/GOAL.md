---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- src/cluster_analysis.py
- src/cli/chunk.py
- src/hooks.py
- src/templates/plugin/skills/audit-corpus.md.jinja2
- skills/audit-corpus/SKILL.md
- tests/test_chunk_partition.py
- tests/test_plugin_skills.py
- tests/test_plugin_render.py
- docs/subsystems/cluster_analysis/OVERVIEW.md
code_references: []
narrative: null
investigation: null
subsystems:
- subsystem_id: cluster_analysis
  relationship: implements
- subsystem_id: workflow_artifacts
  relationship: uses
- subsystem_id: template_system
  relationship: uses
friction_entries: []
depends_on: []
created_after:
- external_never_resolved
- hooks_lifecycle_fragments
- claudemd_marker_safety
- claudemd_symlink_notice
- template_workspace_awareness
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

VE ships an `audit-corpus` plugin skill that reports the health of a project's
entire chunk corpus — validity, freshness, accuracy, and redundancy — and a
`ve chunk partition` CLI command that supplies the skill with a deterministic,
machine-readable partition of that corpus.

The partition is computed by the CLI from data VE already records, never by a
classifier agent. `ve chunk partition --json` groups chunks under two
independent relations: **code overlap** (chunks claiming the same file, drawn
from `code_paths` and `code_references`, with shared symbols reported as
stronger evidence) and **content similarity** (TF-IDF over GOAL.md text). The
skill consumes that assignment and fans out sub-agents over it. Because the
grouping is deterministic, two runs over an unchanged corpus produce the same
clusters and therefore the same findings.

The code-overlap relation is an overlapping **cover**, not a strict partition: a
chunk claiming five files belongs to five clusters. Grouping by connected
component instead — unioning chunks transitively through the files they share —
collapses a real corpus into a single cluster, because A shares one file with B
while B shares a different file with C. On this repository that put 423 of 454
chunks in one component, at every fan-in ceiling tried. A cover loses nothing
the audit needs: two chunks can only be redundant if they claim a file in
common, and that file's cluster contains both.

The skill separates the audit by locality, and that separation is the
load-bearing design decision:

- **Per-chunk checks are local.** A chunk over-claims, or points at a moved
  file, or holds a status that no longer describes its ownership, independently
  of every other chunk. These shard arbitrarily, N chunks per agent, and cost
  scales linearly.
- **Redundancy is relational.** Two chunks are only comparable when they land in
  the same agent's context, and naive pairwise comparison is O(n²) —
  intractable on the thousand-chunk corpora this skill exists for. The CLI
  partition is what makes the relational pass affordable: one agent per cluster,
  and chunks in different clusters are never compared.

The skill reports; it does not rewrite. Every finding lands as a proposed action
against a named chunk, and resolving redundancy — superseding, merging into a
narrative, marking COMPOSITE, historicalizing — stays an operator decision. The
skill is therefore safe to run against a corpus its operator did not author.

`audit-corpus` complements the existing `audit-intent` skill
(`skills/audit-intent/SKILL.md`) rather than replacing it. `audit-intent` is a
one-time migration that *rewrites* chunks to the present-tense standard in
`docs/trunk/CHUNKS.md`. `audit-corpus` is a recurring health report whose
distinct axis is redundancy and cross-chunk contradiction. Where the two overlap
on per-chunk accuracy, `audit-corpus` delegates to the existing `intent-auditor`
agent (`agents/intent-auditor.md`) in a read-only mode rather than restating its
detection criteria.

## Success Criteria

### The CLI partition

- `ve chunk partition --json` emits, for every chunk in scope, its cluster
  assignment under both relations, in one invocation. Shape (illustrative):
  ```json
  {
    "relations": {
      "code_overlap": [{"id": "c0", "members": ["a", "b"], "evidence": ["src/x.py"]}],
      "content_similarity": [{"id": "s0", "members": ["a", "q"], "score": 0.41, "theme": "…"}]
    },
    "unclustered": ["z"],
    "high_fan_in_paths": [{"path": "src/ve.py", "chunk_count": 50}]
  }
  ```
- Nothing in scope is silently dropped. Chunks that neither relation grouped
  appear in `unclustered`; hub files excluded from the overlap relation appear
  in `high_fan_in_paths` with the count that excluded them. A run that bounded
  its own coverage has to say so, or a partial audit reads as a complete one.
- The command reuses `src/cluster_analysis.py#cluster_chunks` for TF-IDF
  similarity rather than reimplementing it, and reuses `src/symbols.py`'s
  `qualify_ref` / `parse_reference` so the overlap relation and
  `src/chunks.py#Chunks.find_overlapping_chunks` agree on what a reference
  points at. The overlap relation itself is new code:
  `find_overlapping_chunks` answers a different question (for one chunk, which
  ACTIVE *ancestors* share a reference — directional, status-locked, and
  `code_references`-only), and calling it per chunk would be the quadratic cost
  the clustering exists to avoid.
- `--min-similarity` is accepted and defaults consistently with
  `ve chunk cluster` (currently 0.3).
- Status filtering matches `ve chunk list` (`--status`, plus the `--active`
  style shortcuts), so an operator can audit only ACTIVE chunks or include
  HISTORICAL.
- Tests assert deterministic output for a fixture corpus: the same input
  produces byte-identical cluster assignment across runs.

### The skill

- `src/templates/plugin/skills/audit-corpus.md.jinja2` exists, renders via
  `ve plugin render` to `skills/audit-corpus/SKILL.md`, and passes the
  invariants in `tests/test_plugin_skills.py` (frontmatter, no un-rendered
  Jinja2, AUTO-GENERATED header). It uses the shared `idioms.frontmatter` and
  `canonical_preamble` partials like every other plugin skill.
- The skill defines the four audit axes explicitly, so two runs mean the same
  thing by them:
  - **Validity** — the chunk's references resolve. The skill *calls*
    `ve validate` for this and reports its findings; it does not re-derive
    reference integrity the validator already owns.
  - **Freshness** — the code the chunk governs still matches what the chunk
    claims about it, and the chunk's status still answers "how much of the
    intent does this chunk own?" correctly.
  - **Accuracy** — the GOAL's assertions are true of the code (over-claim
    detection), delegated to the `intent-auditor` agent in report-only mode.
  - **Redundancy** — two or more chunks claim overlapping intent over the same
    code, making them candidates for COMPOSITE co-ownership, supersession, or
    consolidation into a narrative.
- Execution has two passes with different partitioning, and the skill states
  why: an arbitrary-shard per-chunk pass, and a one-agent-per-cluster relational
  pass driven by `ve chunk partition --json`.
- Multi-tree repositories are in scope: the skill enumerates member trees via
  `ve chunk list --workspace` and audits each tree's corpus with its own
  partition. Cross-tree redundancy is explicitly out of scope and the skill says
  so — references crossing a tree boundary belong to `ve workspace validate`.
- The run is scopeable and resumable. The operator can audit the whole corpus, a
  named cluster, or only chunks touched since a git ref; an interrupted run
  resumes without repeating completed clusters. A run that bounds its own
  coverage says what it skipped — silent truncation reads as "audited
  everything".
- Output is a findings report carrying a proposed action per finding, plus
  `docs/trunk/INCONSISTENCIES/` entries for doc-vs-code contradictions in the
  format `audit-intent` already established. No chunk file is rewritten and no
  status is changed by the skill itself.
- Redundancy findings name the resolution the operator would run
  (`ve chunk status`, `ve narrative create`, `ve chunk cluster-rename`) rather
  than describing the problem abstractly.
- The skill is validated end-to-end against this repository's own corpus — 451
  chunks at the time of writing, 391 of them ACTIVE — and the run produces
  findings a reader can act on without re-reading the chunks themselves.

### Whole-repo hygiene

- `uv run ve validate` exits zero.
- `uv run pytest tests/` passes.
- `ve plugin render` is re-run and the rendered `skills/audit-corpus/SKILL.md`
  is committed alongside its template.

## Implementation notes

Prior art to read before planning:

- `skills/audit-intent/SKILL.md` — the wave-based fan-out pattern, the
  INCONSISTENCIES entry format, and the veto rule.
- `agents/intent-auditor.md` — the per-chunk audit protocol this skill
  delegates to.
- `src/cluster_analysis.py` — `cluster_chunks` (TF-IDF), `get_chunk_clusters`
  (prefix clusters), `check_cluster_size`.
- `src/chunks.py` — `find_overlapping_chunks`, `compute_symbolic_overlap`.
- `src/cli/chunk.py` — `cluster`, `overlap`, `cluster_list_cmd`; where
  `partition` will live.
- `src/plugin_render.py` — how a `skills/*.md.jinja2` template becomes
  `skills/<name>/SKILL.md`.

Naming: the skill is `audit-corpus`, pairing with the existing `audit-intent`.
The CLI subcommand is `ve chunk partition` — `cluster` and `cluster-list` are
taken and mean narrower things.

## Rejected Ideas

### An LLM classifier agent as the dispatch front door

The obvious shape is: one agent reads the corpus, classifies chunks by area of
interest, and dispatches each group to a sub-agent. Rejected on three grounds.

It does not fit. A thousand-chunk corpus does not fit in one agent's context, so
the classifier becomes its own recursive fan-out problem — partitioning in order
to partition.

It does not converge. LLM classification is not reproducible, so successive runs
reshuffle clusters and findings churn between runs instead of the corpus getting
measurably cleaner.

It re-derives what VE already records. `code_paths`, `code_references`,
`subsystems`, `narrative`, and `depends_on` are exactly the "area of interest"
signal, already written down, and VE already carries both the code-overlap and
TF-IDF clustering implementations. Judgment is spent inside a cluster — "is this
genuine redundancy or complementary work?" — where a heuristic genuinely cannot
answer and an LLM can.

### Subsuming audit-intent into the new skill

Rejected: `audit-intent` is a migration with a terminal state (a corpus
rewritten to the present-tense standard), while `audit-corpus` is a recurring
report with no terminal state. Merging them would give a destructive one-time
operation the same entry point as a safe repeatable one.

### Auto-fixing redundancy findings

Rejected: superseding or merging chunks destroys intent records, and whether two
overlapping chunks are redundant or deliberately co-owning (COMPOSITE) is a
judgment the operator has to make. Even the narrower "auto-fix only the
mechanically unambiguous" option was declined, to keep the skill safe to run
against a corpus the operator did not author.

### Computing the partition in the skill's bash instead of the CLI

Rejected: the partition logic would live in prose, could not be unit-tested, and
would drift from `ve chunk cluster`'s existing similarity math. A CLI command is
testable, reproducible, and reusable — the orchestrator's conflict oracle
(`src/orchestrator/oracle.py`) needs the same overlap relation.