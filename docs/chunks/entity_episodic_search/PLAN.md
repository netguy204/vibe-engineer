

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Build `src/entity_episodic.py` as a new pure-Python module containing all
BM25 indexing and expansion logic, then wire it into a new `ve entity episodic`
CLI command in `src/cli/entity.py`.

**What we're building on:**
- `src/entity_transcript.py` — already has `parse_session_jsonl()`,
  `is_substantive_turn()`, `SessionTranscript`, and `Turn`. Use them directly.
- `src/entities.py` — `Entities.entity_dir(name)` gives us `.entities/<name>/`.
  The `sessions/` subdirectory and `sessions.jsonl` log are already established
  by the `entity_session_tracking` chunk.
- The prototype at `docs/investigations/entity_session_harness/prototypes/` —
  `search_experiment.py` and `expand_experiment.py` are proven implementations.
  Translate them directly into the production module.

**Architecture:**
- `EpisodicChunk` dataclass: `session_id`, `chunk_id`, `text`, `timestamp`,
  `anchor_start` (original turn index), `anchor_end` (original turn index)
- `BM25Index` class: standard BM25 scoring (k1=1.5, b=0.75), pure Python
- `EpisodicStore` class: manages the index cache on disk and orchestrates
  search + expand operations
- Index cache: `.entities/<name>/episodic_index/index.json` — JSON dict with
  `indexed_sessions` list, `chunks` list, `doc_freqs` dict, `doc_lengths` list,
  `tokenized_docs` list-of-lists

**Testing strategy (TDD):** Write failing tests first for each unit of behavior.
Follow the project's "semantic assertions over structural assertions" principle.

## Subsystem Considerations

No existing subsystems are relevant to this chunk's scope.

## Sequence

### Step 1: Write failing unit tests for `entity_episodic.py`

Create `tests/test_entity_episodic.py` with tests for each behavioral unit before
writing any implementation code.

Tests to write:

**Tokenizer:**
- `test_tokenize_lowercases_and_strips_punctuation` — "Hello, World!" → ["hello", "world"]
- `test_tokenize_removes_stop_words` — "the cat in the hat" → ["cat", "hat"]
- `test_tokenize_handles_empty_string` — returns []

**Chunk builder:**
- `test_build_chunks_sliding_window_of_5` — a transcript with 10 substantive turns
  produces chunks of 5, stepping by 2-3
- `test_build_chunks_anchors_map_to_original_turns` — anchor_start/anchor_end are
  indices into the *original* transcript.turns list, not into the filtered list
- `test_build_chunks_empty_transcript_returns_empty` — transcript with no substantive
  turns returns []
- `test_build_chunks_filters_insubstantive_turns` — turns with <20 chars are excluded
  from chunk windows

**BM25 search:**
- `test_bm25_search_returns_relevant_results` — index 3 chunks, query a term present
  in only 1, verify that chunk ranks first with score > 0
- `test_bm25_search_empty_corpus_returns_empty` — building over 0 chunks and searching
  returns []
- `test_bm25_search_unknown_query_term_returns_empty` — no chunk contains the term,
  returns empty list
- `test_bm25_score_degrades_gracefully_with_multi_term_partial_matches` — chunk with 2
  of 3 query terms scores lower than chunk with all 3

**EpisodicStore indexing:**
- `test_build_or_update_indexes_sessions_directory` — point store at a temp entity dir
  containing a `sessions/` subdirectory with one real JSONL file; after build_or_update,
  the index contains chunks from that session
- `test_build_or_update_skips_already_indexed_sessions` — call build_or_update twice;
  second call does not re-index the same session (indexed_sessions list unchanged)
- `test_build_or_update_incremental_adds_new_sessions` — initial index has session A;
  add session B to the sessions dir; rebuild adds B without losing A's chunks
- `test_build_or_update_handles_no_sessions_directory` — entity dir has no `sessions/`
  subdir; build_or_update returns empty index without error

**EpisodicStore search:**
- `test_search_returns_ranked_results_with_metadata` — after indexing a JSONL fixture,
  searching for a term present in the transcript returns SearchResult objects with
  session_id, chunk_id, score, timestamp, text preview
- `test_search_result_includes_expand_command_hint` — each result includes a formatted
  expand command string (for copy-paste)

**EpisodicStore expand:**
- `test_expand_returns_surrounding_context` — given a session JSONL and a chunk whose
  anchor is turn 10, expand with radius=2 returns turns 8–12 at minimum
- `test_expand_marks_hit_region_with_arrows` — turns within anchor_start..anchor_end
  are prefixed with `>>>`, others with `   `
- `test_expand_clamps_to_transcript_boundaries` — chunk at the start of a transcript
  (anchor_start=0) expands without IndexError

Location: `tests/test_entity_episodic.py`

### Step 2: Implement `src/entity_episodic.py`

Create the module with the following structure:

**Imports and constants:**
```python
# Chunk: docs/chunks/entity_episodic_search
```

- Import `parse_session_jsonl`, `is_substantive_turn`, `SessionTranscript`, `Turn`
  from `entity_transcript`
- Define stop words constant (same set as the prototype)
- BM25 params: `K1 = 1.5`, `B = 0.75`, `WINDOW_SIZE = 5`, `WINDOW_STEP = 2`

**`tokenize(text: str) -> list[str]`:**
- Lowercase, replace `[^\w\s]` with space, split, filter stopwords and len < 2
- Same logic as the prototype's `tokenize()`, lifted verbatim

**`EpisodicChunk` dataclass:**
```python
@dataclass
class EpisodicChunk:
    session_id: str
    chunk_id: int       # global index across all sessions in the corpus
    text: str           # cleaned window text for indexing and display
    timestamp: str      # ISO 8601 from the first turn in the window
    anchor_start: int   # original transcript.turns index of first window turn
    anchor_end: int     # original transcript.turns index of last window turn
```

**`build_chunks(transcript: SessionTranscript, base_chunk_id: int = 0) -> list[EpisodicChunk]`:**
- Filter `transcript.turns` to substantive turns, recording their original indices
- Slide a window of `WINDOW_SIZE` over the filtered list, stepping by `WINDOW_STEP`
- For each window, build `text` by joining `[ROLE]: cleaned_text` per turn
  (use `clean_text()` from `entity_transcript` — already imported)
- `anchor_start` = original index of `substantive_indices[i]`
- `anchor_end` = original index of `substantive_indices[min(i+WINDOW_SIZE-1, last)]`
- `chunk_id` = `base_chunk_id + window_number`
- Return the list of `EpisodicChunk`

**`BM25Index` dataclass:**
```python
@dataclass
class BM25Index:
    chunks: list[EpisodicChunk]
    doc_freqs: dict[str, int]      # term → num docs containing it
    doc_lengths: list[int]
    avg_doc_length: float
    tokenized_docs: list[list[str]]
    k1: float = K1
    b: float = B
```

- `BM25Index.build(chunks) -> BM25Index` classmethod: tokenize all chunks,
  compute doc_freqs, doc_lengths, avg_doc_length
- `BM25Index.search(query: str, top_k: int = 5) -> list[tuple[EpisodicChunk, float]]`:
  standard BM25 IDF × TF-norm scoring; return top_k with score > 0, sorted descending

**`SearchResult` dataclass:**
```python
@dataclass
class SearchResult:
    rank: int
    score: float
    session_id: str
    chunk_id: int
    timestamp: str      # date portion for display
    preview: str        # first 200 chars of chunk text
    expand_cmd: str     # copy-pasteable expand command
```

**`EpisodicStore` class:**

```python
class EpisodicStore:
    def __init__(self, entity_dir: Path):
        self._entity_dir = entity_dir

    @property
    def sessions_dir(self) -> Path:
        return self._entity_dir / "sessions"

    @property
    def index_path(self) -> Path:
        return self._entity_dir / "episodic_index" / "index.json"
```

- `_load_raw() -> dict`: read `index.json`; return `{"indexed_sessions": [],
  "chunks": [], "doc_freqs": {}, "doc_lengths": [], "tokenized_docs": []}` if missing
- `_save_raw(data: dict)`: write `index.json`; create parent dir if needed
- `build_or_update(entity_name: str) -> None`:
  - List `.jsonl` files in `sessions_dir`; if dir missing, return early
  - Load raw data; compute `new_sessions` = files whose stem not in `indexed_sessions`
  - For each new session JSONL: call `parse_session_jsonl()`, `build_chunks()` with
    `base_chunk_id=len(existing_chunks)`, append chunks to `data["chunks"]`,
    append session_id to `data["indexed_sessions"]`
  - Rebuild `doc_freqs`, `doc_lengths`, `tokenized_docs` from all chunks
    (recompute from scratch — the incremental cost is trivial given the corpus size)
  - Save updated data
- `search(query: str, top_k: int = 5, entity_name: str = "") -> list[SearchResult]`:
  - Load raw data; reconstruct `BM25Index` from it
  - Call `BM25Index.search()`; convert results to `SearchResult` with formatted
    `expand_cmd` = `ve entity episodic --entity {entity_name} --expand {session_id} --chunk {chunk_id}`
  - Return list
- `expand(session_id: str, chunk_id: int, radius: int = 10) -> str`:
  - Load raw data; find the `EpisodicChunk` with matching `session_id` and `chunk_id`
  - Load the full transcript: `parse_session_jsonl(sessions_dir / f"{session_id}.jsonl")`
  - Expand `[anchor_start - radius, anchor_end + radius]` within transcript.turns bounds
  - For each turn in range: skip if empty text; format as `>>> [ROLE TIMESTAMP]: text`
    if `anchor_start <= i <= anchor_end`, else `   [ROLE TIMESTAMP]: text`
  - Return joined lines

Location: `src/entity_episodic.py`

### Step 3: Write failing CLI tests

Create `tests/test_entity_episodic_cli.py` with Click CliRunner tests:

**Search mode:**
- `test_episodic_search_prints_ranked_results` — invoke
  `ve entity episodic --entity <name> --query "keyword"` against a temp entity dir
  containing a seeded sessions/ JSONL; verify exit_code=0 and output contains
  "score=", "session=", "expand:"
- `test_episodic_search_no_results_prints_no_results_message` — query a term that
  doesn't appear in any transcript; verify output says "No results"
- `test_episodic_search_missing_entity_exits_nonzero` — entity does not exist in
  project_dir; verify exit_code != 0

**Expand mode:**
- `test_episodic_expand_prints_context_with_markers` — invoke
  `ve entity episodic --entity <name> --expand <session_id> --chunk 0 --radius 5`;
  verify output contains `>>>` markers
- `test_episodic_expand_missing_session_exits_nonzero` — session_id not found in
  sessions dir; verify exit_code != 0

**Test fixture helper:**
Create a `_make_session_jsonl(path, turns)` helper that writes a minimal valid
Claude Code JSONL fixture (user + assistant entries with required fields), reusable
across tests.

Location: `tests/test_entity_episodic_cli.py`

### Step 4: Add `episodic` command to `src/cli/entity.py`

Add the `episodic` subcommand to the existing `entity` Click group:

```python
@entity.command("episodic")
@click.option("--entity", "entity_name", required=True, help="Entity name")
@click.option("--query", default=None, help="Search query (search mode)")
@click.option("--expand", "expand_session", default=None, metavar="SESSION_ID",
              help="Session ID to expand around (expand mode)")
@click.option("--chunk", "expand_chunk_id", type=int, default=None,
              help="Chunk ID to expand (required with --expand)")
@click.option("--radius", default=10, show_default=True,
              help="Number of turns to include before/after in expand mode")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path),
              default=None)
def episodic(entity_name, query, expand_session, expand_chunk_id, radius, project_dir):
```

**Search mode** (when `--query` is provided):
1. Resolve `project_dir` via `resolve_entity_project_dir()`
2. Validate entity exists; raise `ClickException` if not
3. Instantiate `EpisodicStore(entities.entity_dir(entity_name))`
4. Call `store.build_or_update(entity_name)` to refresh the index
5. Call `store.search(query, entity_name=entity_name)`
6. If no results: `click.echo("No results for ...")`; return
7. Print header: `Results for "{query}" ({n} matches across {m} sessions):`
8. For each result, print:
   ```
   [{rank}] score={score:.2f} session={session_id[:8]} date={date}
       {preview}
       → expand: {expand_cmd}
   ```

**Expand mode** (when `--expand` is provided):
1. Require `--chunk` to be provided; raise `ClickException` if missing
2. Resolve project/entity as above
3. Instantiate `EpisodicStore`
4. Call `store.expand(expand_session, expand_chunk_id, radius)`; if not found, raise `ClickException`
5. Print the expanded context

**Mutual exclusion / validation:**
- Exactly one of `--query` or `--expand` must be provided; print usage hint if neither

Location: `src/cli/entity.py`

### Step 5: Update `GOAL.md` code_paths and run tests

Update `docs/chunks/entity_episodic_search/GOAL.md` frontmatter `code_paths` to:
```yaml
code_paths:
  - src/entity_episodic.py
  - src/cli/entity.py
  - tests/test_entity_episodic.py
  - tests/test_entity_episodic_cli.py
```

Run `uv run pytest tests/test_entity_episodic.py tests/test_entity_episodic_cli.py -v`
and ensure all tests pass. Then run the full suite to verify no regressions.

## Dependencies

- `entity_session_tracking` chunk must be complete — provides `sessions.jsonl` log
  and the `.entities/<name>/sessions/` archive directory that this chunk reads from.
- `entity_transcript_extractor` chunk must be complete — provides `parse_session_jsonl`,
  `is_substantive_turn`, `clean_text`, `SessionTranscript`, `Turn` in
  `src/entity_transcript.py`.

Both are declared in GOAL.md `depends_on`. The directory and file interfaces they
establish are assumed to exist.

## Risks and Open Questions

- **Index cache size**: The `tokenized_docs` field serialized to JSON could become
  large for entities with dozens of long sessions. For the expected corpus size (tens
  of sessions, hundreds of chunks), this is fine. Monitor and switch to a more compact
  format (e.g., pickle) if needed.
- **JSONL file encoding**: `parse_session_jsonl` already handles malformed lines with
  a `try/except json.JSONDecodeError`. The JSONL fixture format in tests should mirror
  the minimal required fields from `entity_transcript.py` to avoid unexpected parse
  behavior.
- **Chunk ID stability**: `chunk_id` is a global integer assigned at build time.
  After an incremental rebuild (adding new sessions), existing chunk IDs remain stable
  because we use `base_chunk_id = len(existing_chunks)` and append only. This means
  expand commands remain valid after new sessions are indexed.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
