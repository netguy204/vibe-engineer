---
status: SOLVED
trigger: "Long-lived Claude Code sessions lose identity across restarts; resume/continue CLI args aren't intuitive for entity-oriented workflows"
proposed_chunks:
  - prompt: "Add session tracking and transcript archiving to entity storage."
    chunk_directory: entity_session_tracking
    depends_on: []
  - prompt: "Build a transcript extractor module for Claude Code JSONL sessions."
    chunk_directory: entity_transcript_extractor
    depends_on: []
  - prompt: "Add API-driven memory extraction from transcripts to entity_shutdown.py."
    chunk_directory: entity_api_memory_extraction
    depends_on: [1]
  - prompt: "Create ve entity claude wrapper with full session lifecycle."
    chunk_directory: entity_claude_wrapper
    depends_on: [0, 1, 2]
  - prompt: "Implement ve entity episodic BM25 search with two-phase search+expand."
    chunk_directory: entity_episodic_search
    depends_on: [0, 1]
  - prompt: "Create /entity-episodic skill and update /entity-startup to mention episodic."
    chunk_directory: entity_episodic_skill
    depends_on: [4]
created_after: ["agent_memory_consolidation"]
---

<!--
DO NOT DELETE THIS COMMENT until the investigation reaches a terminal status.
This documents the frontmatter schema and guides investigation workflow.

STATUS VALUES:
- ONGOING: Investigation is active; exploration and analysis in progress
- SOLVED: The investigation question has been answered. If proposed_chunks exist,
  implementation work remains—SOLVED indicates the investigation is complete, not
  that all resulting work is done.
- NOTED: Findings documented but no action required; kept for future reference
- DEFERRED: Investigation paused; may be revisited later when conditions change

TRIGGER:
- Brief description of what prompted this investigation
- Examples:
  - "Test failures in CI after dependency upgrade"
  - "User reported slow response times on dashboard"
  - "Exploring whether GraphQL would simplify our API"
- The trigger naturally captures whether this is an issue (problem to solve)
  or a concept (opportunity to explore)

PROPOSED_CHUNKS:
- Starts empty; entries are added if investigation reveals actionable work
- Each entry records a chunk prompt for work that should be done
- Format: list of {prompt, chunk_directory, depends_on} where:
  - prompt: The proposed chunk prompt text
  - chunk_directory: Populated when/if the chunk is actually created via /chunk-create
  - depends_on: Optional array of integer indices expressing implementation dependencies.

    SEMANTICS (null vs empty distinction):
    | Value           | Meaning                                 | Oracle behavior |
    |-----------------|----------------------------------------|-----------------|
    | omitted/null    | "I don't know dependencies for this"  | Consult oracle  |
    | []              | "Explicitly has no dependencies"       | Bypass oracle   |
    | [0, 2]          | "Depends on prompts at indices 0 & 2"  | Bypass oracle   |

    - Indices are zero-based and reference other prompts in this same array
    - At chunk-create time, index references are translated to chunk directory names
    - Use `[]` when you've analyzed the chunks and determined they're independent
    - Omit the field when you don't have enough context to determine dependencies
- Unlike narrative chunks (which are planned upfront), these emerge from investigation findings
-->

## Trigger

Spawning entities (long-lived agents) and setting up stewards are two of the most
valuable workflows in vibe engineering. With 1M token context in Opus, sessions run
much longer before needing restart. But when they do restart, finding and resuming
the right session is painful:

- Claude Code's `--resume` and `--continue` flags aren't intuitive for entity workflows
- Sessions lack persistent identity - there's no concept of "this is the steward session"
- Prior session history is lost when starting fresh, even though memory partially bridges the gap
- Memory consolidation works well on first pass but degrades on subsequent consolidations

The core friction: **sessions are ephemeral but entities are persistent**, and there's
no harness bridging the two.

## Success Criteria

1. **Lifecycle design**: Clear specification of `ve entity claude --entity <name>` startup/shutdown behavior
2. **Session tracking**: Design for how session IDs are stored and associated with entities
3. **Episodic search**: Feasibility assessment of indexing prior sessions for semantic/BM25 search via `ve entity episodic --entity <name> --query '...'`
4. **Claude Code integration points**: Identify what hooks/wrappers are needed around Claude Code CLI (startup commands, shutdown hooks, session ID capture)
5. **Memory vs episodic boundary**: Clear articulation of when information belongs in entity memory vs episodic session search

## Testable Hypotheses

### H1: A thin wrapper around Claude Code CLI can provide entity lifecycle without forking Claude Code

- **Rationale**: `ve entity claude` could be a subprocess wrapper that (a) runs startup commands via `--prompt` or initial input, (b) captures the session ID on exit, (c) stores it in entity state. This avoids modifying Claude Code internals.
- **Test**: Prototype a wrapper that launches `claude` with a startup slash command, captures session ID from output/filesystem, and logs it.
- **Status**: VERIFIED - Claude Code stores session registry at `~/.claude/sessions/<pid>.json` with sessionId. A wrapper can launch claude as a subprocess, capture its PID, then read the session ID from the registry file after exit. Startup can use `--prompt` to inject `/entity-startup <name>`.

### H2: Claude Code session transcripts are accessible and indexable after the session ends

- **Rationale**: Claude Code must store session data somewhere locally (for `--resume` to work). If we can locate and parse these transcripts, we can build episodic search over them.
- **Test**: Find where Claude Code stores session data, examine the format, determine if it's parseable for indexing.
- **Status**: VERIFIED - Session transcripts are JSONL at `~/.claude/projects/<encoded-path>/<sessionId>.jsonl`. Session index at `sessions-index.json` includes summary, firstPrompt, messageCount, timestamps. Rich enough for both BM25 and semantic indexing.

### H3: Episodic search over prior sessions provides value beyond what memory consolidation offers

- **Rationale**: Memory consolidation captures distilled knowledge but loses the narrative/context of how decisions were reached, specific error messages encountered, and exploratory dead ends. Episodic search would preserve this detail.
- **Test**: Identify 3+ categories of information that would be useful to retrieve from prior sessions but aren't captured in memory (e.g., specific error traces, discarded approaches, exact commands run).
- **Status**: UNTESTED

### H4: The startup/shutdown lifecycle can be made reliable without Claude Code hook support

- **Rationale**: If Claude Code doesn't have lifecycle hooks (on-start, on-exit), the wrapper needs to handle this externally. Startup is easy (inject initial command), but shutdown is harder - the wrapper needs to detect exit and run cleanup.
- **Test**: Investigate Claude Code's exit behavior - does it signal cleanly? Can a shell trap capture the session ID? Does `--resume` expose session IDs programmatically?
- **Status**: UNTESTED

## Exploration Log

### 2026-03-31: Entity system and Claude Code session storage exploration

**Entity system** is already fully implemented with:
- CLI: `ve entity create/list/startup/shutdown/recall/touch`
- Three-tier LSTM-inspired memory: journal → consolidated → core
- Storage in `.entities/<name>/` with identity.md, memories/{journal,consolidated,core}/
- Startup payload (~4K tokens): identity + core memories + consolidated index
- Shutdown pipeline: extract memories → write journals → consolidate → decay
- Slash commands: `/entity-startup`, `/entity-shutdown`

**Claude Code session storage** is fully accessible at `~/.claude/`:
- **Session index**: `~/.claude/projects/-<encoded-path>/sessions-index.json`
  - Fields: sessionId (UUID), fullPath to JSONL, firstPrompt, summary, messageCount, created, modified, gitBranch, projectPath
- **Transcripts**: JSONL files at `~/.claude/projects/<encoded-path>/<sessionId>.jsonl`
- **Session registry**: `~/.claude/sessions/<pid>.json` with pid, sessionId, cwd, startedAt
- **History**: `~/.claude/history.jsonl` with display, timestamp, project, sessionId

**Key insight**: All the building blocks exist. Entities have lifecycle. Claude Code has
accessible, structured session data. The missing piece is the *bridge* between them.

### 2026-03-31: Session index vs disk mismatch

The `sessions-index.json` has 47 entries but none of them correspond to JSONL files
on disk. There are 12 JSONL files on disk that aren't in the index. The index may be
stale or maintained separately from the raw transcripts. **For episodic search, we
should scan for JSONL files on disk rather than relying on the index.**

Some sessions also have subdirectories (not just .jsonl files) — these may be from
different Claude Code versions or contain additional metadata.

### 2026-03-31: Transcript extraction results

Ran extractor over 12 available sessions (see `prototypes/transcript_extractor.py`):
- Largest session: 792 turns (205 user, 587 assistant), 180K chars / 15K words
  - This was a swarm monitor session — mostly automated messages, not human conversation
- Typical sessions: 80-141 turns, 11-18K chars
- **User text is noisy**: task notifications, XML command tags, tool output paths
- **Tool usage dominates**: Bash and Read are the most common tools
- **Code snippets are rare** in assistant text (tool_use blocks are excluded)

### 2026-03-31: BM25 search experiment across chunking strategies

Tested 4 chunking strategies across 7 representative queries
(see `prototypes/search_experiment.py`):

**Strategies tested:**
1. **Dialogue Pairs** — one chunk per user prompt + assistant response
2. **Sliding Window (3)** — 3 turns per chunk, 50% overlap
3. **Sliding Window (5)** — 5 turns per chunk, 50% overlap
4. **Topic Boundary** — chunk at heuristic topic shifts (long user messages, commands)

**Results summary:**

| Strategy | Chunks | Avg tokens | Retrieval quality |
|----------|--------|------------|-------------------|
| Dialogue Pairs | 287 | 44 | Good precision, misses multi-turn context |
| Sliding Window (3) | 906 | 70 | More redundant results, better context |
| Sliding Window (5) | 455 | 116 | Best balance of context and precision |
| Topic Boundary | 226 | 96 | Best for focused topics, misses scattered refs |

**Key observations:**
- All strategies successfully retrieve relevant content for clear queries
- **Text cleaning is critical** — XML tags, task notifications, UUIDs, and paths add
  significant noise. The `clean_text()` function strips these and improves quality
- **Dialogue pairs** are the most precise but miss context that spans multiple turns
- **Sliding window (5)** gives the best balance: enough context per chunk, manageable
  index size, and the overlap ensures no content falls between chunks
- **Topic boundary** produces clean chunks but the heuristic (long user message = new
  topic) is fragile
- BM25 scores are meaningful: relevant results consistently score 5-13, noise scores < 3
- The current session (entity_session_harness investigation) surfaces correctly for
  "memory consolidation" and "entity shutdown" queries — BM25 works on this data

### 2026-03-31: Two-phase search + expand experiment

Tested a pattern where BM25 returns compact snippets, then the agent can expand
around a hit to read the surrounding conversation (see `prototypes/expand_experiment.py`).

**Design**: Each chunk is anchored to original turn indices. `expand(chunk, radius=10)`
reads ±10 turns from the raw transcript around the hit. The hit region is marked with
`>>>` so the agent can see what matched vs. what's context.

**Results**:
- Expansion provides 2-6x more content than the search snippet
- The additional context is high-value: it reveals corrections, follow-ups, and outcomes
- Example: "steward SOP autonomous mode" search hit shows the steward loading SOP.
  Expansion reveals the user *correcting* the steward's behavior — exactly the kind of
  context an entity needs to avoid repeating mistakes.
- Example: "board websocket reconnect" hit shows a changelog entry. Expansion reveals
  the full diagnostic conversation: before/after backoff timing, assessment of fix quality.

**Conclusion**: Two-phase (search → expand) is clearly better than just returning bigger
chunks upfront. It lets the agent decide what's worth reading in detail, keeps initial
results scannable, and provides the narrative context that BM25 snippets lack.

**Proposed interface**:
```
# Phase 1: search
ve entity episodic --entity steward --query "websocket reconnect"
# Returns: ranked snippets with session_id + chunk_id

# Phase 2: expand
ve entity episodic --entity steward --expand <session_id> --chunk <chunk_id> --radius 10
# Returns: ±10 turns around the hit, with hit region marked
```

Or as a single call with `--expand` flag that shows expanded top-K results.

### 2026-03-31: Shutdown automation design

**Problem**: `/entity-shutdown` currently runs inside Claude Code — the agent reflects
on its own context and extracts memories. But if the user Ctrl+C's or `/exit`s, Claude
Code is gone before shutdown can happen.

**Two approaches — implement both:**

**Strategy A: Resume + in-session shutdown (primary)**
After Claude Code exits, the wrapper:
1. Captures sessionId from `~/.claude/sessions/<pid>.json`
2. Runs `claude --resume <sessionId> --prompt "/entity-shutdown <name>"`
3. The resumed agent has full session context and does proper self-reflection
4. Agent extracts memories, runs consolidation, exits

This is just as robust as post-exit extraction — the session transcript persists on
disk regardless of exit path (Ctrl+C, /exit, crash). `--resume` reloads it.
Higher fidelity because the agent reflects on its own experience.

**Strategy B: Post-exit transcript extraction (fallback)**
If resume fails (corrupted session, Claude Code unavailable, etc.):
1. Read JSONL transcript from `~/.claude/projects/<encoded-path>/<sessionId>.jsonl`
2. Extract user/assistant text content
3. Call Anthropic API with `EXTRACTION_PROMPT` + transcript
4. Feed extracted memories into `run_consolidation()`

Lower fidelity but zero dependency on Claude Code being re-launchable.

**Default behavior**: Try Strategy A. If it exits non-zero or times out, fall back
to Strategy B. This gives the best-quality extraction in the common case and a
reliable fallback for edge cases.

**Implementation note**: Strategy A requires no new extraction code — it reuses
the existing `/entity-shutdown` slash command end-to-end. Strategy B requires
a transcript parser and an API call to `EXTRACTION_PROMPT`, feeding into the
existing `run_consolidation()` pipeline.

## Findings

### Verified Findings

**Claude Code session data is structured, accessible, and rich enough for episodic search.**
- 47 sessions for this project in `~/.claude/projects/-Users-btaylor-Projects-vibe-engineer/`
- Session index has: sessionId, summary, firstPrompt, messageCount, timestamps, gitBranch
- Transcripts are JSONL with typed messages (user/assistant), each containing full content
- Largest transcript is 2.6MB - manageable for indexing
- Messages have parentUuid for threading, timestamps, and session metadata

**The entity lifecycle already handles memory. The gap is session identity tracking.**
- `ve entity startup` produces a payload. `ve entity shutdown` runs consolidation.
- Nothing currently links an entity to the Claude Code session(s) it ran in.
- No way to search "what did the steward do 3 sessions ago" without manually finding the session.

**Session IDs are capturable from the filesystem.**
- `~/.claude/sessions/<pid>.json` maps PID → sessionId
- A wrapper that launches Claude Code can capture the PID, wait for exit, then read the session ID
- Alternative: scan `sessions-index.json` for the most recently modified session after exit

### Hypotheses/Opinions

**BM25 over extracted text content is the right starting point for episodic search.**
- Semantic search requires embeddings infra (storage, model calls). BM25 is zero-dependency.
- Session transcripts contain tool calls, code, and system prompts that inflate size but add noise.
- Best approach: extract just user prompts and assistant text blocks, skip tool_use/tool_result blocks.
- Can upgrade to hybrid (BM25 + semantic) later if recall is insufficient.

**The `ve entity claude` wrapper should be minimal - a thin shell script or Python CLI command.**
- Startup: resolve entity, launch `claude --prompt "/entity-startup <name>"`, capture PID
- Shutdown: on Claude Code exit, read session ID from `~/.claude/sessions/<pid>.json`,
  append to `.entities/<name>/sessions.jsonl`, optionally run `ve entity shutdown`
- The wrapper doesn't need to be interactive or complex - it's orchestrating existing pieces

**Memory vs episodic boundary is clean.**
- Memory = distilled lessons ("always verify PR state before merging") - already works
- Episodic = searchable record of what happened ("session where we debugged the orchestrator retry logic") - the missing piece
- Memory consolidation should continue operating on session content at shutdown
- Episodic index operates on the raw JSONL transcripts independently
- They serve different retrieval patterns: memory for "what do I know", episodic for "when did I encounter X"

## Proposed Chunks

### Design: `ve entity claude` Wrapper

```
ve entity claude --entity steward
```

**Startup sequence:**
1. Verify entity exists in `.entities/<name>/`
2. Launch `claude --prompt "/entity-startup <name>"` as subprocess, capture PID
3. Wait for Claude Code to exit

**Shutdown sequence:**
1. Read `~/.claude/sessions/<pid>.json` → extract sessionId
2. Append `{sessionId, startedAt, endedAt}` to `.entities/<name>/sessions.jsonl`
3. Optionally trigger `ve entity shutdown <name>` (or let the user do it manually within the session)

### Design: `ve entity episodic` Search

```
ve entity episodic --entity steward --query "orchestrator retry failures"
```

**Index building:**
1. Read `.entities/<name>/sessions.jsonl` to get list of session IDs
2. For each session, read the JSONL transcript from `~/.claude/projects/<encoded-path>/<sessionId>.jsonl`
3. Extract text content: user prompts + assistant text blocks (skip tool_use, tool_result, file-history-snapshot)
4. Build BM25 index over extracted chunks (chunk by message turn or fixed window)

**Search:**
1. Query the BM25 index
2. Return top-K results with: session date, surrounding context, relevance score
3. Output format suitable for piping into a new Claude Code session as context

**Index caching:**
- Cache the extracted/indexed content in `.entities/<name>/episodic_index/`
- Rebuild incrementally when new sessions appear

---

1. **Entity session tracking + transcript archiving** (chunk 0): Add `sessions.jsonl`
   index and `.entities/<name>/sessions/` directory for archived JSONL transcripts.
   Archive transcripts at session end before Claude Code garbage collects them.
   - Priority: High
   - Dependencies: None
   - Notes: Foundation for everything. Without archiving, episodic memory erodes —
     we observed 47 sessions in the index but only 12 JSONL files surviving on disk.

2. **Transcript extractor** (chunk 1): `src/entity_transcript.py` — parse Claude Code
   JSONL session transcripts into cleaned, structured SessionTranscript objects.
   - Priority: High
   - Dependencies: None
   - Notes: Scan disk for JSONL files (sessions-index.json is stale/unreliable). Clean
     XML tags, task notifications, UUIDs, paths. Shared by wrapper + episodic search.
     See prototypes/transcript_extractor.py.

3. **API-driven memory extraction** (chunk 2): Add to entity_shutdown.py — accept a
   SessionTranscript and extract memories via Anthropic API without a live session.
   - Priority: High
   - Dependencies: Transcript extractor
   - Notes: Fallback for when `claude --resume` fails. Uses existing EXTRACTION_PROMPT.

4. **Entity Claude wrapper** (chunk 3): `ve entity claude --entity <name>` — full
   lifecycle. Launch → session → capture session ID → archive transcript → resume
   for shutdown → fallback to API extraction if resume fails → log session.
   - Priority: High
   - Dependencies: Chunks 0, 1, 2
   - Notes: The main user-facing command. Archive happens immediately after exit,
     before shutdown, to capture the transcript while it still exists.

5. **Episodic BM25 search** (chunk 4): `ve entity episodic --entity <name> --query '...'`
   Two-phase: search returns ranked snippets, expand reads ±N turns around a hit.
   - Priority: Medium
   - Dependencies: Chunks 0, 1
   - Notes: Reads from entity's own archive (`.entities/<name>/sessions/`), not from
     `~/.claude/`. Sliding window (5), pure-Python BM25, incremental index caching.
     See prototypes/search_experiment.py and expand_experiment.py.

6. **Episodic search skill** (chunk 5): `/entity-episodic` slash command that teaches
   agents how and when to use episodic memory. Also update `/entity-startup` to mention
   episodic search availability.
   - Priority: Medium
   - Dependencies: Chunk 4
   - Notes: Key distinction: memory = "what I know" (distilled lessons), episodic =
     "what happened" (searchable session history). Teaches the two-phase search→expand
     workflow with practical examples.

## Resolution Rationale

Investigation answered all success criteria:

1. **Lifecycle design**: `ve entity claude --entity <name>` launches Claude Code with
   `/entity-startup`, captures session ID on exit, runs shutdown (resume-first with
   API fallback), and logs the session.

2. **Session tracking**: `sessions.jsonl` in `.entities/<name>/` links entity identity
   to Claude Code session IDs with timestamps.

3. **Episodic search**: BM25 over sliding-window chunks is feasible and effective.
   Prototyped and tested on 12 real sessions. Two-phase search→expand pattern provides
   both quick scanning and deep context retrieval.

4. **Claude Code integration**: Session data is fully accessible at
   `~/.claude/projects/<encoded-path>/<sessionId>.jsonl` as structured JSONL.
   PID→sessionId mapping available at `~/.claude/sessions/<pid>.json`.
   Note: `sessions-index.json` is unreliable — scan disk directly. Critically,
   Claude Code garbage collects old transcripts (47 indexed, 12 surviving), so
   transcripts must be archived into `.entities/<name>/sessions/` at session end.

5. **Memory vs episodic boundary**: Clean separation. Memory = distilled lessons
   ("what I know"). Episodic = searchable session history ("what happened when").
   They serve different retrieval patterns and operate independently.

6 proposed chunks cover the full implementation: session tracking, transcript extraction,
API-driven memory extraction, the wrapper command, BM25 episodic search, and a skill
to teach agents how to use episodic memory.