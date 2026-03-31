---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/entity_episodic.py
  - src/cli/entity.py
  - tests/test_entity_episodic.py
  - tests/test_entity_episodic_cli.py
code_references:
  - ref: src/entity_episodic.py#tokenize
    implements: "BM25 tokenizer — lowercase, strip punctuation, remove stop words"
  - ref: src/entity_episodic.py#EpisodicChunk
    implements: "Sliding-window chunk dataclass with session/anchor metadata"
  - ref: src/entity_episodic.py#build_chunks
    implements: "Sliding window (size=5, step=2) chunking of substantive transcript turns"
  - ref: src/entity_episodic.py#BM25Index
    implements: "Pure-Python BM25 index (k1=1.5, b=0.75) — build and search"
  - ref: src/entity_episodic.py#SearchResult
    implements: "Search result dataclass with rank, score, preview, and expand command"
  - ref: src/entity_episodic.py#EpisodicStore
    implements: "Index cache management (build_or_update, search, expand) in .entities/<name>/episodic_index/"
  - ref: src/cli/entity.py#episodic
    implements: "ve entity episodic CLI — search and expand modes"
narrative: null
investigation: entity_session_harness
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_session_tracking
- entity_transcript_extractor
created_after:
- entity_session_tracking
---
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