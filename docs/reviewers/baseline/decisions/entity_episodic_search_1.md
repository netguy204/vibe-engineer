---
decision: APPROVE
summary: "All seven success criteria satisfied — BM25 search, expand, incremental index caching, pure-Python implementation, and full test coverage all work correctly."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve entity episodic --entity <name> --query "..."` returns ranked BM25 results from archived transcripts

- **Status**: satisfied
- **Evidence**: `src/cli/entity.py` episodic command search mode calls `store.build_or_update()` then `store.search()`. `EpisodicStore.search()` reconstructs `BM25Index` from cached data and returns ranked `SearchResult` list. CLI test `test_episodic_search_prints_ranked_results` verifies exit_code=0 and ranked output.

### Criterion 2: Results include session ID, date, score, text preview, and a copy-pasteable expand command

- **Status**: satisfied
- **Evidence**: `SearchResult` dataclass (`src/entity_episodic.py:183`) has `session_id`, `timestamp` (date portion), `score`, `preview` (first 200 chars), and `expand_cmd` (formatted as `ve entity episodic --entity {name} --expand {session_id} --chunk {chunk_id}`). CLI prints all fields. Test `test_search_result_includes_expand_command_hint` verifies `--expand` and `--chunk` are present.

### Criterion 3: `ve entity episodic --entity <name> --expand <session> --chunk <id>` shows surrounding context with `>>>` markers on the hit

- **Status**: satisfied
- **Evidence**: `EpisodicStore.expand()` (`src/entity_episodic.py:333`) formats turns in `[anchor_start, anchor_end]` with `>>>` prefix and context turns with `   ` prefix. CLI test `test_episodic_expand_prints_context_with_markers` verifies `>>>` in output.

### Criterion 4: Index is cached in `.entities/<name>/episodic_index/` and rebuilt incrementally

- **Status**: satisfied
- **Evidence**: `index_path` property returns `entity_dir / "episodic_index" / "index.json"`. `build_or_update()` computes `new_sessions = files whose stem not in indexed_sessions` and only processes those. Tests `test_build_or_update_skips_already_indexed_sessions` and `test_build_or_update_incremental_adds_new_sessions` verify this behavior.

### Criterion 5: Reads exclusively from `.entities/<name>/sessions/` (entity's archive), not `~/.claude/`

- **Status**: satisfied
- **Evidence**: `sessions_dir` property returns `entity_dir / "sessions"`. No reference to `~/.claude/` anywhere in `entity_episodic.py` or the CLI command. The `entity_dir` is always derived from `entities.entity_dir(entity_name)`.

### Criterion 6: No external dependencies (pure Python BM25)

- **Status**: satisfied
- **Evidence**: `src/entity_episodic.py` imports only stdlib (`json`, `math`, `re`, `collections`, `dataclasses`, `pathlib`) and the project-internal `entity_transcript` module. BM25 scoring is hand-implemented (IDF × TF-norm, `k1=1.5`, `b=0.75`) at lines 147–175.

### Criterion 7: Tests cover indexing, search, expansion, incremental rebuild, and empty corpus

- **Status**: satisfied
- **Evidence**: 25 tests all pass. Coverage includes: tokenizer (3), chunk builder (4), BM25 (4), store indexing (4 — including incremental and no-sessions-dir), store search (2), store expand (3 — including boundary clamping), and CLI (5 — search, no-results, missing entity, expand with markers, missing session).
