---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: entity_session_harness
subsystems: []
friction_entries: []
bug_type: null
depends_on: ["entity_session_tracking", "entity_transcript_extractor"]
created_after: ["entity_session_tracking"]
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

Implement `ve entity episodic` — a two-phase search tool for querying an entity's
archived session transcripts. Agents use this to recall what happened in prior sessions:
specific errors, conversations, decisions, debugging sequences, and operator corrections
in their original context.

### How it differs from entity memory

- **Memory** (`ve entity recall`) = distilled lessons. "Always check PR state before acting."
- **Episodic** (`ve entity episodic`) = searchable history. "The session where we debugged the orchestrator retry logic and the operator corrected my approach to merge conflicts."

Memory is what you know. Episodic is what happened.

### Two-phase workflow

**Phase 1: Search** — find relevant snippets across all archived sessions

```
ve entity episodic --entity steward --query "websocket reconnect"
```

Output: ranked list of matching snippets with session ID, timestamp, score, and
a text preview. The agent scans these to decide which are worth expanding.

**Phase 2: Expand** — read the surrounding conversation around a hit

```
ve entity episodic --entity steward --expand <session_id> --chunk <chunk_id> --radius 10
```

Output: ±N turns from the raw transcript around the search hit. The hit region is
marked with `>>>` so the agent can see what matched vs. what's surrounding context.
This is where the value is — the agent sees the full narrative: what led to the
decision, what correction followed, what the outcome was.

### What to build

**1. New module** `src/entity_episodic.py`:

**Chunking** — sliding window of 5 substantive turns with 50% overlap:
- Read transcripts from `.entities/<name>/sessions/<sessionId>.jsonl` (the entity's archive, NOT `~/.claude/`)
- Use `parse_session_jsonl()` from `entity_transcript.py` to extract turns
- Filter with `is_substantive_turn()`
- Create overlapping windows of 5 turns, stepping by 2-3

**BM25 index** — pure Python, no external dependencies:
- Tokenizer: lowercase, strip punctuation, remove common stop words
- Standard BM25 scoring: IDF * TF with length normalization (k1=1.5, b=0.75)
- Each chunk stores: session_id, chunk_id, text, timestamp, and anchor indices
  (mapping back to original turn positions for expansion)

**Index caching** in `.entities/<name>/episodic_index/`:
- Cache the tokenized chunks and document frequencies
- Track which session IDs are indexed
- Rebuild incrementally when `sessions.jsonl` has sessions not yet in the index
- Use a simple JSON or pickle format

**Expansion**:
- Given a session_id + chunk_id, load the full archived transcript
- Find the turn range that corresponds to the chunk (via anchors)
- Expand ±radius turns from the original (uncleaned) transcript
- Mark the hit region with `>>>` prefix, context with `   ` prefix
- Format as: `>>> [ROLE TIMESTAMP]: text`

**2. CLI commands** in `src/cli/entity.py`:

```
ve entity episodic --entity <name> --query "..."        # search mode
ve entity episodic --entity <name> --expand <session_id> --chunk <chunk_id> [--radius 10]  # expand mode
```

**3. Output format** for search mode (agent-friendly):

```
Results for "websocket reconnect" (3 matches across 2 sessions):

[1] score=7.81 session=aa040a20 date=2026-03-16
    pybusiness 6.22.0 merged to main — database savings plans work is fully
    landed. All 4 channels monitored...
    → expand: ve entity episodic --entity steward --expand aa040a20 --chunk 42

[2] score=7.24 session=aa040a20 date=2026-03-16
    Two consecutive clean watches — the WebSocket stability fix is solid...
    → expand: ve entity episodic --entity steward --expand aa040a20 --chunk 38
```

Each result includes the expand command so the agent can copy-paste it.

### Reference prototypes

Working prototypes exist at:
- `docs/investigations/entity_session_harness/prototypes/search_experiment.py` — BM25 + chunking strategies
- `docs/investigations/entity_session_harness/prototypes/expand_experiment.py` — two-phase search + expand

These were tested on 12 real sessions. The sliding window (5) strategy with BM25
produced good results across 7 test queries. Use them as reference for the
production implementation.

### Design decisions from investigation

- **Sliding window (5)** was chosen over dialogue pairs (too fragmented), window(3)
  (too many redundant results), and topic boundary (fragile heuristics)
- **Pure Python BM25** — no external dependencies. The index is small enough
  (hundreds of chunks across dozens of sessions) that performance isn't a concern
- **Expand radius defaults to 10** — provides 2-6x more content than the search
  snippet, which is the right amount for understanding context

## Success Criteria

- `ve entity episodic --entity <name> --query "..."` returns ranked BM25 results from archived transcripts
- Results include session ID, date, score, text preview, and a copy-pasteable expand command
- `ve entity episodic --entity <name> --expand <session> --chunk <id>` shows surrounding context with `>>>` markers on the hit
- Index is cached in `.entities/<name>/episodic_index/` and rebuilt incrementally
- Reads exclusively from `.entities/<name>/sessions/` (entity's archive), not `~/.claude/`
- No external dependencies (pure Python BM25)
- Tests cover indexing, search, expansion, incremental rebuild, and empty corpus

## Rejected Ideas

### Semantic search with embeddings

Embedding-based search would provide better recall for conceptual queries. Rejected
for now because it requires an embeddings model dependency, storage for vectors, and
a similarity search implementation. BM25 is zero-dependency and performed well in
prototyping. Can be layered on later if BM25 recall proves insufficient.

### Including tool results in searchable text

Tool results (Bash output, file contents, etc.) contain useful information like error
messages. Rejected because they are extremely noisy (full file contents, large diffs)
and would dominate the index. Tool names are captured (so you can search for "Bash"
or "Edit") but tool input/output is excluded. This can be revisited if agents report
missing important error context.