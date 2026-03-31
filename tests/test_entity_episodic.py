"""Unit tests for entity_episodic module."""

import json
from pathlib import Path

import pytest

from entity_episodic import tokenize, EpisodicChunk, build_chunks, BM25Index, SearchResult, EpisodicStore
from entity_transcript import Turn, SessionTranscript


def _make_turn(role, text, timestamp="2026-01-01T00:00:00Z", uuid="abc"):
    return Turn(role=role, text=text, timestamp=timestamp, uuid=uuid)


def _make_session_jsonl(path: Path, turns: list[dict]) -> Path:
    """Write a minimal valid Claude Code JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for i, turn in enumerate(turns):
            entry = {
                "type": turn.get("type", "user"),
                "uuid": turn.get("uuid", f"uuid-{i}"),
                "timestamp": turn.get("timestamp", "2026-01-01T00:00:00.000Z"),
                "requestId": turn.get("requestId", f"req-{i}"),
                "message": {
                    "content": turn.get("text", "Hello world, this is a test turn with enough content."),
                },
            }
            f.write(json.dumps(entry) + "\n")
    return path


class TestTokenize:
    def test_tokenize_lowercases_and_strips_punctuation(self):
        tokens = tokenize("Hello, World!")
        assert "hello" in tokens
        assert "world" in tokens
        assert "Hello," not in tokens

    def test_tokenize_removes_stop_words(self):
        tokens = tokenize("the cat in the hat")
        assert tokens == ["cat", "hat"]

    def test_tokenize_handles_empty_string(self):
        assert tokenize("") == []


class TestBuildChunks:
    def test_build_chunks_sliding_window_of_5(self):
        # Create 10 substantive turns (each >20 chars)
        turns = [
            _make_turn("user" if i % 2 == 0 else "assistant",
                       f"This is a substantive turn number {i} with enough content.")
            for i in range(10)
        ]
        transcript = SessionTranscript(session_id="test_session", turns=turns)
        chunks = build_chunks(transcript)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert "[USER]:" in chunk.text or "[ASSISTANT]:" in chunk.text

    def test_build_chunks_anchors_map_to_original_turns(self):
        # turns[0] is insubstantive (<20 chars), turns[1..] are substantive
        turns = [
            _make_turn("user", "Short"),  # insubstantive, index 0
            _make_turn("user", "This is a substantive user message with enough content."),  # index 1
            _make_turn("assistant", "This is a substantive assistant response with enough content."),  # index 2
            _make_turn("user", "Another substantive user message with enough content here."),  # index 3
            _make_turn("assistant", "Another substantive assistant response with enough content."),  # index 4
            _make_turn("user", "Yet another substantive user message with enough content."),  # index 5
        ]
        transcript = SessionTranscript(session_id="test_anchor", turns=turns)
        chunks = build_chunks(transcript)
        assert len(chunks) >= 1
        # First chunk should start at turn index 1 (first substantive turn), not 0
        assert chunks[0].anchor_start == 1

    def test_build_chunks_empty_transcript_returns_empty(self):
        transcript = SessionTranscript(session_id="empty", turns=[])
        assert build_chunks(transcript) == []

    def test_build_chunks_filters_insubstantive_turns(self):
        turns = [
            _make_turn("user", "Hi"),   # <20 chars, insubstantive
            _make_turn("user", "Hey"),  # <20 chars, insubstantive
            _make_turn("user", "This is a substantive user message with enough content."),
            _make_turn("assistant", "This is a substantive assistant response with enough content."),
        ]
        transcript = SessionTranscript(session_id="filter_test", turns=turns)
        chunks = build_chunks(transcript)
        # Should produce chunks; insubstantive turns not in text
        assert len(chunks) >= 1
        for chunk in chunks:
            assert "Hi" not in chunk.text or "This is" in chunk.text


class TestBM25Index:
    def _make_chunk(self, session_id, chunk_id, text):
        return EpisodicChunk(
            session_id=session_id,
            chunk_id=chunk_id,
            text=text,
            timestamp="2026-01-01T00:00:00Z",
            anchor_start=0,
            anchor_end=4,
        )

    def test_bm25_search_returns_relevant_results(self):
        chunks = [
            self._make_chunk("s1", 0, "The cat sat on the mat with fur"),
            self._make_chunk("s1", 1, "websocket reconnect logic handles dropped connections"),
            self._make_chunk("s1", 2, "database migration scripts for schema updates"),
        ]
        idx = BM25Index.build(chunks)
        results = idx.search("websocket reconnect")
        assert len(results) > 0
        top_chunk, top_score = results[0]
        assert top_chunk.chunk_id == 1
        assert top_score > 0

    def test_bm25_search_empty_corpus_returns_empty(self):
        idx = BM25Index.build([])
        assert idx.search("anything") == []

    def test_bm25_search_unknown_query_term_returns_empty(self):
        chunks = [
            self._make_chunk("s1", 0, "The quick brown fox jumps over the lazy dog"),
        ]
        idx = BM25Index.build(chunks)
        results = idx.search("xyzzy_never_exists_in_corpus")
        assert results == []

    def test_bm25_score_degrades_gracefully_with_multi_term_partial_matches(self):
        chunks = [
            self._make_chunk("s1", 0, "alpha beta gamma delta epsilon zeta"),  # has all 3 query terms
            self._make_chunk("s1", 1, "alpha beta other things here for context"),  # has 2 of 3
        ]
        idx = BM25Index.build(chunks)
        results = idx.search("alpha beta gamma")
        assert len(results) == 2
        # Chunk with all 3 terms should score higher
        assert results[0][0].chunk_id == 0
        assert results[0][1] > results[1][1]


class TestEpisodicStoreIndexing:
    def test_build_or_update_indexes_sessions_directory(self, tmp_path):
        entity_dir = tmp_path / "entity"
        sessions_dir = entity_dir / "sessions"
        _make_session_jsonl(
            sessions_dir / "session_abc.jsonl",
            turns=[
                {"type": "user", "text": "This is a substantive user message about websocket reconnect logic."},
                {"type": "assistant", "text": "The websocket reconnect logic handles dropped connections automatically."},
            ] * 5,
        )

        store = EpisodicStore(entity_dir)
        store.build_or_update()

        assert store.index_path.exists()
        data = json.loads(store.index_path.read_text())
        assert len(data["chunks"]) > 0

    def test_build_or_update_skips_already_indexed_sessions(self, tmp_path):
        entity_dir = tmp_path / "entity"
        sessions_dir = entity_dir / "sessions"
        _make_session_jsonl(
            sessions_dir / "session_abc.jsonl",
            turns=[
                {"type": "user", "text": "Substantive message about first session content."},
                {"type": "assistant", "text": "Assistant response with enough content to be indexed."},
            ] * 5,
        )

        store = EpisodicStore(entity_dir)
        store.build_or_update()

        data1 = json.loads(store.index_path.read_text())
        indexed_count1 = len(data1["indexed_sessions"])

        # Second call should not re-index
        store.build_or_update()

        data2 = json.loads(store.index_path.read_text())
        indexed_count2 = len(data2["indexed_sessions"])

        assert indexed_count1 == indexed_count2

    def test_build_or_update_incremental_adds_new_sessions(self, tmp_path):
        entity_dir = tmp_path / "entity"
        sessions_dir = entity_dir / "sessions"

        # Index session A
        _make_session_jsonl(
            sessions_dir / "session_a.jsonl",
            turns=[
                {"type": "user", "text": "Substantive message from session A about data processing."},
                {"type": "assistant", "text": "The data processing pipeline runs incrementally for efficiency."},
            ] * 5,
        )

        store = EpisodicStore(entity_dir)
        store.build_or_update()
        data1 = json.loads(store.index_path.read_text())
        chunks_count1 = len(data1["chunks"])

        # Add session B
        _make_session_jsonl(
            sessions_dir / "session_b.jsonl",
            turns=[
                {"type": "user", "text": "Substantive message from session B about caching strategy."},
                {"type": "assistant", "text": "The caching strategy uses LRU eviction with configurable TTL."},
            ] * 5,
        )

        store.build_or_update()
        data2 = json.loads(store.index_path.read_text())
        chunks_count2 = len(data2["chunks"])

        # More chunks after adding session B
        assert chunks_count2 > chunks_count1
        # Both sessions indexed
        assert "session_a" in data2["indexed_sessions"]
        assert "session_b" in data2["indexed_sessions"]

    def test_build_or_update_handles_no_sessions_directory(self, tmp_path):
        entity_dir = tmp_path / "entity"
        entity_dir.mkdir(parents=True)
        # No sessions subdir

        store = EpisodicStore(entity_dir)
        # Should not raise
        store.build_or_update()
        # No index created
        assert not store.index_path.exists()


class TestEpisodicStoreSearch:
    def test_search_returns_ranked_results_with_metadata(self, tmp_path):
        entity_dir = tmp_path / "entity"
        sessions_dir = entity_dir / "sessions"
        _make_session_jsonl(
            sessions_dir / "session_abc.jsonl",
            turns=[
                {"type": "user", "text": "How does the websocket reconnect mechanism handle connection drops?"},
                {"type": "assistant", "text": "The websocket reconnect logic automatically retries connection drops."},
            ] * 5,
        )

        store = EpisodicStore(entity_dir)
        store.build_or_update()
        results = store.search("websocket reconnect", entity_name="test_entity")

        assert len(results) > 0
        r = results[0]
        assert r.session_id == "session_abc"
        assert r.chunk_id >= 0
        assert r.score > 0
        assert r.timestamp != ""
        assert len(r.preview) > 0

    def test_search_result_includes_expand_command_hint(self, tmp_path):
        entity_dir = tmp_path / "entity"
        sessions_dir = entity_dir / "sessions"
        _make_session_jsonl(
            sessions_dir / "session_abc.jsonl",
            turns=[
                {"type": "user", "text": "Substantive user message about database migration strategy."},
                {"type": "assistant", "text": "The database migration applies schema changes incrementally."},
            ] * 5,
        )

        store = EpisodicStore(entity_dir)
        store.build_or_update()
        results = store.search("database migration", entity_name="test_entity")

        assert len(results) > 0
        for r in results:
            assert "--expand" in r.expand_cmd
            assert "--chunk" in r.expand_cmd


class TestEpisodicStoreExpand:
    def _make_20_turn_session(self, tmp_path):
        entity_dir = tmp_path / "entity"
        sessions_dir = entity_dir / "sessions"
        turns = []
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            turns.append({
                "type": role,
                "text": f"This is turn number {i} with enough substantive content to be indexed by search.",
            })
        _make_session_jsonl(sessions_dir / "session_long.jsonl", turns=turns)
        return entity_dir, sessions_dir

    def test_expand_returns_surrounding_context(self, tmp_path):
        entity_dir, _ = self._make_20_turn_session(tmp_path)
        store = EpisodicStore(entity_dir)
        store.build_or_update()

        data = json.loads(store.index_path.read_text())
        # Find a chunk near the middle
        chunks = data["chunks"]
        # pick one with anchor_start around turn 8-12
        mid_chunk = None
        for c in chunks:
            if 5 <= c["anchor_start"] <= 12:
                mid_chunk = c
                break

        if mid_chunk is None:
            # Just use first chunk
            mid_chunk = chunks[0]

        expanded = store.expand(mid_chunk["session_id"], mid_chunk["chunk_id"], radius=5)
        assert expanded is not None
        assert len(expanded) > 0

    def test_expand_marks_hit_region_with_arrows(self, tmp_path):
        entity_dir, _ = self._make_20_turn_session(tmp_path)
        store = EpisodicStore(entity_dir)
        store.build_or_update()

        data = json.loads(store.index_path.read_text())
        chunk = data["chunks"][0]

        expanded = store.expand(chunk["session_id"], chunk["chunk_id"], radius=3)
        assert expanded is not None
        assert ">>>" in expanded

    def test_expand_clamps_to_transcript_boundaries(self, tmp_path):
        entity_dir, _ = self._make_20_turn_session(tmp_path)
        store = EpisodicStore(entity_dir)
        store.build_or_update()

        data = json.loads(store.index_path.read_text())
        # Find chunk with anchor_start == 0 (or the earliest chunk)
        chunks = sorted(data["chunks"], key=lambda c: c["anchor_start"])
        first_chunk = chunks[0]

        # Should not raise IndexError
        expanded = store.expand(first_chunk["session_id"], first_chunk["chunk_id"], radius=100)
        assert expanded is not None
